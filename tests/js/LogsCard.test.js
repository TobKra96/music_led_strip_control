import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import LogsCard from '../../src/mlsc/app/static/assets/js/classes/LogsCard.js';
import { ApiError } from '../../src/mlsc/app/static/assets/js/classes/Api.js';

const INTERVAL = 5000;
const entry = (over = {}) => ({ time: '2026-11-01T10:00:00Z', level: 'info', source: 'a:b:1', message: 'hello', ...over });
const result = (entries, over = {}) => ({ unavailable: null, persistent: true, entries, ...over });

let root;
let api;

const flush = async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); };
const q = (selector) => root.querySelector(selector);
const lines = () => [...root.querySelectorAll('[data-logs-line]')];
const setHidden = (hidden) => {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden });
    document.dispatchEvent(new Event('visibilitychange'));
};

const open = async (response = result([entry()])) => {
    api = { get: vi.fn().mockResolvedValue(response) };
    const card = new LogsCard(root, api, { intervalMs: INTERVAL });
    card.load();
    await flush();
    return card;
};

beforeEach(() => {
    vi.useFakeTimers();
    setHidden(false);
    document.body.innerHTML = '<div id="logs"></div>';
    root = document.getElementById('logs');
});

afterEach(() => {
    vi.useRealTimers();
});

it('requests 200 lines with no level and no text by default', async () => {
    await open();

    expect(api.get).toHaveBeenCalledWith('/system/logs?lines=200');
});

it('renders an entry with time, level and message', async () => {
    await open(result([entry({ level: 'warning', message: 'careful <b>' })]));

    const [line] = lines();
    expect(line.querySelector('[data-logs-time]').textContent).not.toBe('');
    expect(line.querySelector('[data-logs-level]').textContent.toLowerCase()).toContain('warning');
    expect(line.querySelector('[data-logs-level]').className).toContain('warning');
    expect(line.querySelector('[data-logs-message]').textContent).toBe('careful <b>');
    expect(line.querySelector('b')).toBeNull();
});

it('renders continuation lines without a time or level', async () => {
    await open(result([entry({ time: null, level: null, source: null, message: '  at line 2' })]));

    expect(lines()).toHaveLength(1);
    expect(q('[data-logs-message]').textContent).toBe('  at line 2');
});

it('scrolls the pane to the bottom after rendering', async () => {
    api = { get: vi.fn().mockResolvedValue(result([entry()])) };
    const card = new LogsCard(root, api);
    const pane = q('[data-logs-pane]');
    Object.defineProperty(pane, 'scrollHeight', { configurable: true, value: 900 });
    card.load();
    await flush();

    expect(pane.scrollTop).toBe(900);
});

it('replaces the pane with the reason when the logs are unavailable', async () => {
    await open(result([], { unavailable: 'journalctl is not installed.', persistent: null }));

    expect(q('[data-logs-unavailable]').textContent).toBe('journalctl is not installed.');
    expect(q('[data-logs-pane]').hidden).toBe(true);
});

it('shows the volatile note when the journal is not persistent', async () => {
    await open(result([entry()], { persistent: false }));

    expect(q('[data-logs-volatile]').hidden).toBe(false);
    expect(q('[data-logs-volatile]').textContent).toBe('Logs are kept in memory and are cleared when the machine restarts.');
});

it('hides the volatile note when the journal is persistent', async () => {
    await open(result([entry()], { persistent: true }));

    expect(q('[data-logs-volatile]').hidden).toBe(true);
});

it('says there are no matching lines for an empty result', async () => {
    await open(result([]));

    expect(q('[data-logs-empty]').textContent).toBe('No matching lines');
    expect(q('[data-logs-empty]').hidden).toBe(false);
    expect(lines()).toHaveLength(0);
});

it('shows an error state when the request fails', async () => {
    api = { get: vi.fn().mockRejectedValue(new ApiError(500, { detail: 'journalctl failed' })) };
    new LogsCard(root, api).load();
    await flush();

    expect(q('[data-logs-error]').textContent).toBe('journalctl failed');
    expect(q('[data-logs-error]').hidden).toBe(false);
});

it('clears the error after a successful refresh', async () => {
    api = { get: vi.fn().mockRejectedValueOnce(new ApiError(500, { detail: 'boom' })).mockResolvedValue(result([entry()])) };
    const card = new LogsCard(root, api);
    card.load();
    await flush();
    card.load();
    await flush();

    expect(q('[data-logs-error]').hidden).toBe(true);
    expect(lines()).toHaveLength(1);
});

it('sends the toolbar values as request params', async () => {
    await open();
    q('[data-logs-filter]').value = 'led strip';
    q('[data-logs-level-select]').value = 'warning';
    q('[data-logs-lines]').value = '500';
    q('[data-logs-refresh]').click();

    expect(api.get).toHaveBeenLastCalledWith('/system/logs?lines=500&level=warning&q=led+strip');
});

it('offers the documented levels and line counts', async () => {
    await open();

    const values = (selector) => [...q(selector).options].map((o) => o.value);
    expect(values('[data-logs-level-select]')).toEqual(['', 'info', 'warning', 'error']);
    expect(values('[data-logs-lines]')).toEqual(['100', '200', '500', '1000']);
    expect(q('[data-logs-lines]').value).toBe('200');
});

it('refreshes when the filter is submitted with Enter', async () => {
    await open();
    q('[data-logs-filter]').value = 'x';
    q('[data-logs-filter]').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));

    expect(api.get).toHaveBeenLastCalledWith('/system/logs?lines=200&q=x');
});

it('does not refresh by itself until auto-refresh is ticked', async () => {
    await open();
    await vi.advanceTimersByTimeAsync(INTERVAL * 3);

    expect(api.get).toHaveBeenCalledTimes(1);
});

it('refreshes on an interval while auto-refresh is ticked', async () => {
    await open();
    q('[data-logs-auto]').click();
    await vi.advanceTimersByTimeAsync(INTERVAL * 2);

    expect(api.get).toHaveBeenCalledTimes(3);
});

it('stops refreshing when auto-refresh is unticked', async () => {
    await open();
    q('[data-logs-auto]').click();
    await vi.advanceTimersByTimeAsync(INTERVAL);
    q('[data-logs-auto]').click();
    await vi.advanceTimersByTimeAsync(INTERVAL * 3);

    expect(api.get).toHaveBeenCalledTimes(2);
});

it('is open by default and collapses from the header', async () => {
    await open();

    expect(q('[data-logs-body]').hidden).toBe(false);
    q('[data-logs-toggle]').click();
    expect(q('[data-logs-body]').hidden).toBe(true);
    expect(q('[data-logs-toggle]').getAttribute('aria-expanded')).toBe('false');
    q('[data-logs-toggle]').click();
    expect(q('[data-logs-body]').hidden).toBe(false);
});

it('pauses auto-refresh while the card is collapsed and resumes when reopened', async () => {
    await open();
    q('[data-logs-auto]').click();
    q('[data-logs-toggle]').click();
    await vi.advanceTimersByTimeAsync(INTERVAL * 3);
    expect(api.get).toHaveBeenCalledTimes(1);

    q('[data-logs-toggle]').click();
    await vi.advanceTimersByTimeAsync(INTERVAL);
    expect(api.get.mock.calls.length).toBeGreaterThanOrEqual(2);
});

it('pauses auto-refresh while the page is hidden and resumes when visible', async () => {
    await open();
    q('[data-logs-auto]').click();
    setHidden(true);
    await vi.advanceTimersByTimeAsync(INTERVAL * 3);
    expect(api.get).toHaveBeenCalledTimes(1);

    setHidden(false);
    await vi.advanceTimersByTimeAsync(INTERVAL);
    expect(api.get.mock.calls.length).toBeGreaterThanOrEqual(2);
});

it('ignores a slow response that was overtaken by a newer one', async () => {
    let first;
    api = {
        get: vi.fn()
            .mockReturnValueOnce(new Promise((resolve) => { first = resolve; }))
            .mockResolvedValue(result([entry({ message: 'new' })])),
    };
    const card = new LogsCard(root, api);
    card.load();
    card.load();
    await flush();
    first(result([entry({ message: 'old' })]));
    await flush();

    expect(lines().map((l) => l.querySelector('[data-logs-message]').textContent)).toEqual(['new']);
});
