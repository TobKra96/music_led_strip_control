import { describe, expect, it, vi } from 'vitest';
import { BrowserMicrophone } from '../../src/mlsc/app/static/assets/js/classes/BrowserMicrophone.js';

const domError = name => Object.assign(new Error(name), { name });

/** A browser stand-in: one fake track, an AudioContext whose worklet node can be fed blocks, and a recording fetch. */
const setup = (overrides = {}) => {
    const track = { stop: vi.fn() };
    const port = {};
    const context = {
        sampleRate: 48000,
        audioWorklet: { addModule: vi.fn().mockResolvedValue() },
        createMediaStreamSource: vi.fn(() => ({ connect: vi.fn() })),
        close: vi.fn().mockResolvedValue(),
    };
    const workletNode = { port, connect: vi.fn() };
    const sentinel = { release: vi.fn().mockResolvedValue() };
    const deps = {
        isSecureContext: true,
        mediaDevices: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [track] }) },
        createContext: vi.fn(() => context),
        createWorkletNode: vi.fn(() => workletNode),
        wakeLock: { request: vi.fn().mockResolvedValue(sentinel) },
        openStream: vi.fn().mockResolvedValue({ stream_id: 'abc' }),
        fetch: vi.fn().mockResolvedValue({ status: 204 }),
        workletUrl: '/worklet.js',
        ...overrides,
    };
    const states = [];
    const microphone = new BrowserMicrophone({ ...deps, onState: (state, detail) => states.push([state, detail]) });
    /** Deliver `count` blocks of 128 samples from the worklet. */
    const feed = async (count) => {
        for (let i = 0; i < count; i++) port.onmessage({ data: new Int16Array(128).fill(1000) });
        await vi.waitFor(() => {});
    };
    return { microphone, deps, track, context, port, sentinel, states, feed };
};

describe('starting', () => {
    it('refuses in an insecure context without asking for the microphone', async () => {
        const { microphone, deps, states } = setup({ isSecureContext: false });

        await microphone.start();

        expect(states.at(-1)[0]).toBe('insecure');
        expect(deps.mediaDevices.getUserMedia).not.toHaveBeenCalled();
    });

    it('turns echo cancellation, noise suppression and auto gain off', async () => {
        const { microphone, deps } = setup();

        await microphone.start();

        expect(deps.mediaDevices.getUserMedia).toHaveBeenCalledWith({
            audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
        });
        expect(microphone.state).toBe('streaming');
    });

    it.each([
        ['NotAllowedError', 'denied'],
        ['NotFoundError', 'no_device'],
    ])('reports %s as %s and does not open a stream', async (name, state) => {
        const { microphone, deps } = setup({ mediaDevices: { getUserMedia: vi.fn().mockRejectedValue(domError(name)) } });

        await microphone.start();

        expect(microphone.state).toBe(state);
        expect(deps.openStream).not.toHaveBeenCalled();
    });
});

describe('streaming', () => {
    const chunkCalls = fetch => fetch.mock.calls.map(([url, options]) => ({ url, ...options }));

    it('opens a stream and sends 40 ms of native-rate PCM per request, numbered from 0', async () => {
        const { microphone, deps, feed } = setup();
        await microphone.start();

        await feed(31); // 31 blocks of 128 samples = 3968 samples = two chunks of 1920 at 48 kHz, with 128 left over

        await vi.waitFor(() => expect(deps.fetch).toHaveBeenCalledTimes(2));
        const [first, second] = chunkCalls(deps.fetch);
        expect(first.url).toBe('/api/v2/microphone/browser/stream/abc/chunks?sequence=0&sample_rate=48000');
        expect(second.url).toBe('/api/v2/microphone/browser/stream/abc/chunks?sequence=1&sample_rate=48000');
        expect(first.method).toBe('POST');
        expect(first.headers['Content-Type']).toBe('application/octet-stream');
        expect(first.body.byteLength).toBe(1920 * 2);
        expect(new Int16Array(first.body.buffer, first.body.byteOffset, 1920).every(v => v === 1000)).toBe(true);
    });

    it('sends the chunks one after another so they arrive in order', async () => {
        let release;
        const fetch = vi.fn().mockImplementationOnce(() => new Promise((resolve) => { release = () => resolve({ status: 204 }); }))
            .mockResolvedValue({ status: 204 });
        const { microphone, feed } = setup({ fetch });
        await microphone.start();

        await feed(30);
        expect(fetch).toHaveBeenCalledTimes(1);

        release();
        await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    });

    it('sends the chunks that piled up behind a slow request together, in order and numbered on', async () => {
        const releases = [];
        const fetch = vi.fn(() => new Promise(resolve => releases.push(() => resolve({ status: 204 }))));
        const { microphone, port } = setup({ fetch });
        await microphone.start();

        // Five chunks of 1920 samples, each marked by its value: the first goes out, four wait.
        for (let i = 1; i <= 5; i++) port.onmessage({ data: new Int16Array(1920).fill(i) });
        await vi.waitFor(() => expect(releases).toHaveLength(1));
        releases.shift()();
        await vi.waitFor(() => expect(releases).toHaveLength(1));

        expect(fetch).toHaveBeenCalledTimes(2);
        const [url, { body }] = fetch.mock.calls[1];
        expect(url).toContain('sequence=1&');
        expect(body.byteLength).toBe(4 * 1920 * 2);
        expect([body[0], body[1920], body[2 * 1920], body[3 * 1920]]).toEqual([2, 3, 4, 5]);
        expect(body.byteLength / 2 / 48000).toBeLessThanOrEqual(1);
    });

    it('drops the oldest audio instead of queueing without limit when the connection stalls', async () => {
        const releases = [];
        const fetch = vi.fn(() => new Promise(resolve => releases.push(() => resolve({ status: 204 }))));
        const { microphone, port } = setup({ fetch });
        await microphone.start();

        for (let i = 1; i <= 40; i++) port.onmessage({ data: new Int16Array(1920).fill(i) });
        await vi.waitFor(() => expect(releases).toHaveLength(1));

        expect(microphone.queued).toHaveLength(15);
        expect(microphone.stats.dropped).toBe(24);
        expect(microphone.backlog).toBe(16);
        releases.shift()();
        await vi.waitFor(() => expect(releases).toHaveLength(1));
        // The newest 15 chunks (26..40) remain, sent as batches of at most 10.
        expect(fetch.mock.calls[1][1].body[0]).toBe(26);
        expect(fetch.mock.calls[1][1].body.length).toBe(10 * 1920);
    });

    it('stops sending queued audio once the stream has ended', async () => {
        const releases = [];
        const fetch = vi.fn(() => new Promise(resolve => releases.push(resolve)));
        const { microphone, port } = setup({ fetch });
        await microphone.start();

        for (let i = 1; i <= 3; i++) port.onmessage({ data: new Int16Array(1920).fill(i) });
        await vi.waitFor(() => expect(releases).toHaveLength(1));
        releases.shift()({ status: 410 });
        await vi.waitFor(() => expect(microphone.state).toBe('stopped'));

        expect(fetch).toHaveBeenCalledTimes(1);
        expect(microphone.queued).toHaveLength(0);
    });
});

describe('ending', () => {
    it.each([401, 403, 410])('stops capturing and says why when the server answers %i', async (status) => {
        const { microphone, track, sentinel, context, states, feed } = setup({ fetch: vi.fn().mockResolvedValue({ status }) });
        await microphone.start();

        await feed(15);

        await vi.waitFor(() => expect(microphone.state).toBe('stopped'));
        expect(states.at(-1)[1]).not.toBe('');
        expect(track.stop).toHaveBeenCalled();
        expect(sentinel.release).toHaveBeenCalled();
        expect(context.close).toHaveBeenCalled();
    });

    it('stops capturing when the connection fails', async () => {
        const { microphone, track, feed } = setup({ fetch: vi.fn().mockRejectedValue(new TypeError('network')) });
        await microphone.start();

        await feed(15);

        await vi.waitFor(() => expect(microphone.state).toBe('error'));
        expect(track.stop).toHaveBeenCalled();
    });

    it('releases the stream on the server when the user stops', async () => {
        const { microphone, deps, track, sentinel, feed } = setup();
        await microphone.start();

        await microphone.stop();
        await feed(15);

        expect(microphone.state).toBe('idle');
        expect(track.stop).toHaveBeenCalled();
        expect(sentinel.release).toHaveBeenCalled();
        expect(deps.fetch).toHaveBeenCalledTimes(1);
        expect(deps.fetch).toHaveBeenCalledWith('/api/v2/microphone/browser/stream/abc', expect.objectContaining({ method: 'DELETE' }));
    });

    it('gives the microphone back when the server refuses the stream', async () => {
        const refused = Object.assign(new Error('Another browser is streaming.'), { status: 409 });
        const { microphone, track } = setup({ openStream: vi.fn().mockRejectedValue(refused) });

        await microphone.start();

        expect(microphone.state).toBe('error');
        expect(track.stop).toHaveBeenCalled();
    });

    it('works without the Screen Wake Lock', async () => {
        const { microphone } = setup({ wakeLock: undefined });

        await microphone.start();

        expect(microphone.state).toBe('streaming');
    });
});

describe('stats', () => {
    it('keeps the slowest block gap, the slowest request and the deepest backlog', async () => {
        let time = 0;
        const releases = [];
        const fetch = vi.fn(() => new Promise(resolve => releases.push(() => { time += 90; resolve({ status: 204 }); })));
        const { microphone, port } = setup({ fetch, now: () => time });
        await microphone.start();

        // Blocks 3 ms apart, then one 40 ms late: the worklet or the tab was held up.
        for (const gap of [0, 3, 3, 40]) {
            time += gap;
            port.onmessage({ data: new Int16Array(960).fill(1000) });
        }
        // The first chunk goes out at 3 ms and the second waits behind it: that request lasts 133 ms, the clock being advanced by the late block and the 90 ms release.
        await vi.waitFor(() => expect(releases).toHaveLength(1));
        expect(microphone.stats.deepestBacklog).toBe(2);
        releases.shift()();
        await vi.waitFor(() => expect(releases).toHaveLength(1));
        releases.shift()();
        await vi.waitFor(() => expect(microphone.stats.requests).toBe(2));

        expect(microphone.stats).toMatchObject({ blocks: 4, slowestBlockGap: 40, slowestRequest: 133 });
        expect(microphone.backlog).toBe(0);
    });
});
