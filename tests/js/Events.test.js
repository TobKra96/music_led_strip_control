import { afterEach, expect, it, vi } from 'vitest';
import { events } from '../../src/mlsc/app/static/assets/js/classes/Events.js';

afterEach(() => {
    events.disconnect();
    vi.unstubAllGlobals();
});

it('closes the stream on disconnect without raising disconnected, and opens a new one on connect', () => {
    const sources = [];
    vi.stubGlobal('EventSource', class {
        constructor() {
            this.close = vi.fn();
            this.addEventListener = vi.fn();
            sources.push(this);
        }
    });
    const disconnected = vi.fn();
    events.on('disconnected', disconnected);

    events.connect();
    events.disconnect();
    events.connect();

    expect(sources).toHaveLength(2);
    expect(sources[0].close).toHaveBeenCalled();
    expect(disconnected).not.toHaveBeenCalled();
});
