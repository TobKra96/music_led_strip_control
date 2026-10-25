/** Length of the audio sent per request. */
const CHUNK_SECONDS = 0.04;

const STOP_REASONS = {
    401: 'Your session ended. Sign in again to stream.',
    403: 'You are not allowed to stream.',
    409: 'The Browser Microphone is not selected or another browser is streaming.',
    410: 'The server released the stream after it stopped receiving audio.',
};

const CONSTRAINTS = { audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } };

/**
 * Streams this browser's microphone to the server as the Browser Microphone.
 * Capture starts only from `start()`, which must run in a user gesture. Nothing resumes by itself.
 *
 * States: `idle`, `starting`, `streaming`, `insecure`, `denied`, `no_device`, `stopped` (the server ended the stream), `error`.
 */
export class BrowserMicrophone {
    /**
     * @param {object} deps The browser APIs, passed in so the stream can be tested without a browser.
     * @param {boolean} deps.isSecureContext
     * @param {MediaDevices} deps.mediaDevices
     * @param {function(): AudioContext} deps.createContext
     * @param {function(AudioContext): AudioWorkletNode} deps.createWorkletNode
     * @param {string} deps.workletUrl
     * @param {{request: function(string): Promise.<{release: function(): Promise}>}|undefined} deps.wakeLock
     * @param {function(): Promise.<{stream_id: string}>} deps.openStream
     * @param {function(string, object): Promise.<{status: number}>} deps.fetch
     * @param {function(string, string=): void} deps.onState Called with the new state and a detail for the user.
     */
    constructor(deps) {
        this.deps = deps;
        this.state = 'idle';
    }

    setState(state, detail = '') {
        this.state = state;
        this.deps.onState(state, detail);
    }

    async start() {
        const { deps } = this;
        if (!deps.isSecureContext) {
            this.setState('insecure');
            return;
        }
        this.setState('starting');
        try {
            this.media = await deps.mediaDevices.getUserMedia(CONSTRAINTS);
        } catch (error) {
            this.setState(error.name === 'NotFoundError' ? 'no_device' : error.name === 'NotAllowedError' ? 'denied' : 'error', error.message);
            return;
        }

        try {
            this.context = deps.createContext();
            await this.context.audioWorklet.addModule(deps.workletUrl);
            const node = deps.createWorkletNode(this.context);
            this.context.createMediaStreamSource(this.media).connect(node);
            // The worklet has to be pulled to run, so it is wired to the destination, where it outputs silence.
            node.connect(this.context.destination);
            this.sampleRate = this.context.sampleRate;
            this.chunkSamples = Math.round(this.sampleRate * CHUNK_SECONDS);
            this.pending = [];
            this.pendingSamples = 0;
            this.sequence = 0;
            this.queue = Promise.resolve();
            this.streamId = (await deps.openStream()).stream_id;
            node.port.onmessage = ({ data }) => this.collect(data);
        } catch (error) {
            await this.release();
            this.setState('error', STOP_REASONS[error.status] || error.message);
            return;
        }
        await this.holdWakeLock();
        this.setState('streaming');
    }

    /** Ask the screen to stay on, where the browser can: a suspended tab stops the stream. */
    async holdWakeLock() {
        try {
            this.sentinel = await this.deps.wakeLock?.request('screen');
        } catch {
            // Denied, for instance on low battery. The page warns about background tabs either way.
        }
    }

    /** @param {Int16Array} block Mono samples from the worklet. */
    collect(block) {
        if (this.state !== 'streaming') return;
        this.pending.push(block);
        this.pendingSamples += block.length;
        while (this.pendingSamples >= this.chunkSamples) {
            const chunk = this.take(this.chunkSamples);
            const sequence = this.sequence++;
            this.queue = this.queue.then(() => this.send(chunk, sequence));
        }
    }

    /** Remove the first `count` samples from the pending blocks. */
    take(count) {
        const chunk = new Int16Array(count);
        let filled = 0;
        while (filled < count) {
            const block = this.pending[0];
            const used = Math.min(block.length, count - filled);
            chunk.set(block.subarray(0, used), filled);
            filled += used;
            if (used === block.length) this.pending.shift();
            else this.pending[0] = block.subarray(used);
        }
        this.pendingSamples -= count;
        return chunk;
    }

    async send(chunk, sequence) {
        if (this.state !== 'streaming') return;
        const url = `/api/v2/microphone/browser/stream/${this.streamId}/chunks?sequence=${sequence}&sample_rate=${this.sampleRate}`;
        let response;
        try {
            response = await this.deps.fetch(url, {
                method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: chunk, keepalive: true, credentials: 'same-origin',
            });
        } catch {
            await this.end('error', 'The connection to the server was lost.');
            return;
        }
        if (response.status === 204) return;
        await this.end('stopped', STOP_REASONS[response.status] || `The server refused the audio (${response.status}).`);
    }

    /** Stop capturing for a reason the user should see. The server side is released on its own after 5 seconds. */
    async end(state, detail) {
        if (this.state !== 'streaming') return;
        this.state = 'ending';
        await this.release();
        this.setState(state, detail);
    }

    async release() {
        this.media?.getTracks().forEach(track => track.stop());
        await this.sentinel?.release().catch(() => {});
        await this.context?.close().catch(() => {});
        this.media = this.sentinel = this.context = null;
    }

    /** Stop streaming and give the claim back to the server. */
    async stop() {
        if (this.state !== 'streaming') return;
        const streamId = this.streamId;
        this.setState('idle');
        // First, so it still goes out when the page is closing.
        const closed = this.deps.fetch(`/api/v2/microphone/browser/stream/${streamId}`, { method: 'DELETE', keepalive: true, credentials: 'same-origin' });
        await this.release();
        await closed.catch(() => {});
    }
}
