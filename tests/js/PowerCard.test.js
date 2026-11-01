import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PowerCard from '../../src/mlsc/app/static/assets/js/classes/PowerCard.js';
import { ApiError } from '../../src/mlsc/app/static/assets/js/classes/Api.js';

const available = { available: true, reason: null };
const blocked = (reason) => ({ available: false, reason });

let root;
let api;
let up;
let navigate;
const follower = () => ({ navigate, fetchFn: async () => { if (!up) throw new TypeError('down'); return { ok: true }; } });

const flush = () => new Promise((resolve) => setTimeout(resolve));
const q = (selector) => root.querySelector(selector);
const button = (action) => q(`[data-power-action="${action}"]`);
const modal = () => q('[data-power-modal]');

const load = async (capabilities, post = vi.fn().mockResolvedValue({ status: 'accepted' })) => {
    api = { get: vi.fn().mockResolvedValue(capabilities), post };
    new PowerCard(root, api, { follower: follower() }).load();
    await flush();
};

beforeEach(() => {
    up = true;
    navigate = vi.fn();
    document.body.innerHTML = '<div id="power"></div>';
    root = document.getElementById('power');
});

it('reads the capabilities from the API on load', async () => {
    await load({ reboot: available, shutdown: available });

    expect(api.get).toHaveBeenCalledWith('/system/power');
});

it('enables both buttons when the host can do both', async () => {
    await load({ reboot: available, shutdown: available });

    expect(button('reboot').disabled).toBe(false);
    expect(button('shutdown').disabled).toBe(false);
    expect(q('[data-power-reason="reboot"]').textContent).toBe('');
});

it('disables a blocked button and shows its reason under it', async () => {
    await load({ reboot: blocked('MLSC does not run as root.'), shutdown: available });

    expect(button('reboot').disabled).toBe(true);
    expect(q('[data-power-reason="reboot"]').textContent).toBe('MLSC does not run as root.');
    expect(button('shutdown').disabled).toBe(false);
});

it('keeps the buttons disabled until the capabilities arrived', () => {
    api = { get: vi.fn().mockReturnValue(new Promise(() => {})), post: vi.fn() };
    new PowerCard(root, api).load();

    expect(button('reboot').disabled).toBe(true);
    expect(button('shutdown').disabled).toBe(true);
});

it('disables both buttons when the capabilities cannot be read', async () => {
    api = { get: vi.fn().mockRejectedValue(new ApiError(0)), post: vi.fn() };
    new PowerCard(root, api).load();
    await flush();

    expect(button('reboot').disabled).toBe(true);
    expect(q('[data-power-reason="reboot"]').textContent).toBe('Unable to reach the server.');
});

it('does not show the modal before a button is clicked', async () => {
    await load({ reboot: available, shutdown: available });

    expect(modal().hidden).toBe(true);
});

it('asks to confirm a reboot and mentions that logs may be cleared', async () => {
    await load({ reboot: available, shutdown: available });
    button('reboot').click();

    expect(modal().hidden).toBe(false);
    expect(q('[data-power-title]').textContent).toBe('Reboot this machine?');
    expect(q('[data-power-body]').textContent).toContain('logs may be cleared');
    expect(api.post).not.toHaveBeenCalled();
});

it('asks to confirm a shutdown and says the machine must be switched on by hand', async () => {
    await load({ reboot: available, shutdown: available });
    button('shutdown').click();

    expect(q('[data-power-title]').textContent).toBe('Shut down this machine?');
    expect(q('[data-power-body]').textContent).toContain('switched on by hand');
});

it('leaves the log line out when the journal is persistent', async () => {
    api = { get: vi.fn().mockResolvedValue({ reboot: available, shutdown: available }), post: vi.fn() };
    new PowerCard(root, api, { logsClearedOnReboot: false }).load();
    await flush();
    button('reboot').click();

    expect(q('[data-power-body]').textContent).not.toContain('logs');
});

it('puts the focus on Cancel and styles the confirm button as dangerous', async () => {
    await load({ reboot: available, shutdown: available });
    button('reboot').click();

    expect(document.activeElement).toBe(q('[data-power-cancel]'));
    expect(q('[data-power-confirm]').classList.contains('btn-danger')).toBe(true);
});

it('closes the modal on Cancel without calling the API', async () => {
    await load({ reboot: available, shutdown: available });
    button('reboot').click();
    q('[data-power-cancel]').click();

    expect(modal().hidden).toBe(true);
    expect(api.post).not.toHaveBeenCalled();
});

it('closes the modal on Escape and returns the focus to the button', async () => {
    await load({ reboot: available, shutdown: available });
    button('shutdown').click();
    modal().dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));

    expect(modal().hidden).toBe(true);
    expect(document.activeElement).toBe(button('shutdown'));
});

it('posts the action on confirm and replaces the card with a banner on 202', async () => {
    await load({ reboot: available, shutdown: available });
    button('reboot').click();
    q('[data-power-confirm]').click();
    await flush();

    expect(api.post).toHaveBeenCalledWith('/system/reboot');
    expect(modal()).toBeNull();
    expect(button('reboot')).toBeNull();
    const banner = q('[data-power-banner]');
    expect(banner.classList.contains('alert-info')).toBe(true);
    expect(banner.textContent).toContain('Rebooting');
});

it('says "Shutting down" after a shutdown', async () => {
    await load({ reboot: available, shutdown: available });
    button('shutdown').click();
    q('[data-power-confirm]').click();
    await flush();

    expect(api.post).toHaveBeenCalledWith('/system/shutdown');
    expect(q('[data-power-banner]').textContent).toContain('Shutting down');
});

it('does not offer a way to dismiss the banner', async () => {
    await load({ reboot: available, shutdown: available });
    button('reboot').click();
    q('[data-power-confirm]').click();
    await flush();

    expect(q('[data-power-banner] button')).toBeNull();
});

it('counts a dropped connection right after the click as going down', async () => {
    await load({ reboot: available, shutdown: available }, vi.fn().mockRejectedValue(new ApiError(0)));
    button('reboot').click();
    q('[data-power-confirm]').click();
    await flush();

    expect(q('[data-power-banner]').textContent).toContain('Rebooting');
    expect(q('[data-power-error]')).toBeNull();
});

it.each([409, 500])('shows the error and keeps the card on %s', async (status) => {
    const error = new ApiError(status, { detail: 'It went wrong.' });
    await load({ reboot: available, shutdown: available }, vi.fn().mockRejectedValue(error));
    button('reboot').click();
    q('[data-power-confirm]').click();
    await flush();

    expect(modal().hidden).toBe(true);
    expect(q('[data-power-error]').textContent).toBe('It went wrong.');
    expect(q('[data-power-banner]')).toBeNull();
    expect(button('reboot')).not.toBeNull();
});

it('clears an earlier error when the next action starts', async () => {
    const post = vi.fn().mockRejectedValueOnce(new ApiError(500, { detail: 'It went wrong.' })).mockResolvedValue({});
    await load({ reboot: available, shutdown: available }, post);
    button('reboot').click();
    q('[data-power-confirm]').click();
    await flush();
    button('reboot').click();

    expect(q('[data-power-error]')).toBeNull();
});

it('ignores a second click on confirm while the request runs', async () => {
    await load({ reboot: available, shutdown: available }, vi.fn().mockReturnValue(new Promise(() => {})));
    button('reboot').click();
    q('[data-power-confirm]').click();
    q('[data-power-confirm]').click();

    expect(api.post).toHaveBeenCalledTimes(1);
});

describe('following the action', () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    const start = async (action, post) => {
        api = { get: vi.fn().mockResolvedValue({ reboot: available, shutdown: available }), post: post || vi.fn().mockResolvedValue({}) };
        new PowerCard(root, api, { follower: follower() }).load();
        await vi.advanceTimersByTimeAsync(0);
        button(action).click();
        q('[data-power-confirm]').click();
        await vi.advanceTimersByTimeAsync(0);
    };
    const banner = () => q('[data-power-banner]').textContent;

    it('waits for the machine to come back after a reboot went down, then goes to /', async () => {
        await start('reboot');
        up = false;
        await vi.advanceTimersByTimeAsync(2000);
        expect(banner()).toContain('Waiting for the machine to come back');
        up = true;
        await vi.advanceTimersByTimeAsync(2000);
        expect(navigate).toHaveBeenCalledWith('/');
    });

    it('keeps saying "Rebooting" while the server still answers', async () => {
        await start('reboot');
        await vi.advanceTimersByTimeAsync(10000);
        expect(banner()).toContain('Rebooting');
        expect(navigate).not.toHaveBeenCalled();
    });

    it('warns with a Reload button after 3 minutes and still redirects on a late return', async () => {
        await start('reboot');
        up = false;
        await vi.advanceTimersByTimeAsync(182000);
        expect(q('[data-power-banner]').classList.contains('alert-warning')).toBe(true);
        expect(q('[data-power-reload]')).not.toBeNull();
        up = true;
        await vi.advanceTimersByTimeAsync(4000);
        expect(navigate).toHaveBeenCalledWith('/');
    });

    it('brings the Power card back with a warning when the machine never went down', async () => {
        await start('reboot');
        await vi.advanceTimersByTimeAsync(30000);
        expect(q('[data-power-error]').textContent).toContain('did not seem to go down');
        expect(button('reboot')).not.toBeNull();
        expect(button('reboot').disabled).toBe(false);
    });

    it('ends with the switch-it-on banner after a shutdown went down', async () => {
        await start('shutdown');
        up = false;
        await vi.advanceTimersByTimeAsync(2000);
        expect(banner()).toContain('Switch it on by hand');
        expect(q('[data-power-reload]')).toBeNull();
    });
});
