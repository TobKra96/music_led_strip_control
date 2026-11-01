import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import PowerFollower, { powerActionPending } from '../../src/mlsc/app/static/assets/js/classes/PowerFollower.js';

let states;
let navigate;
let up;
let followers;

const fetchFn = vi.fn(async () => {
    if (!up) throw new TypeError('Failed to fetch');
    return { ok: true };
});

const follow = (action) => {
    const follower = new PowerFollower(action, (s) => states.push(s), { navigate, fetchFn });
    followers.push(follower);
    follower.start();
    return follower;
};
const advance = (ms) => vi.advanceTimersByTimeAsync(ms);

beforeEach(() => {
    vi.useFakeTimers();
    states = [];
    navigate = vi.fn();
    up = true;
    followers = [];
    fetchFn.mockClear();
});

afterEach(() => {
    followers.forEach((f) => f.stop());
    vi.useRealTimers();
});

it('is not taken for a return while the server still answers after the 202', async () => {
    follow('reboot');
    await advance(10000);

    expect(states).toEqual(['going_down']);
    expect(navigate).not.toHaveBeenCalled();
});

it('polls the session endpoint every 2 s', async () => {
    follow('reboot');
    await advance(6000);

    expect(fetchFn.mock.calls.length).toBe(4);
    expect(fetchFn.mock.calls[0][0]).toBe('/api/v2/auth/session');
});

it('says it waits for the machine once a reboot went down', async () => {
    follow('reboot');
    await advance(3000);
    up = false;
    await advance(2000);

    expect(states).toEqual(['going_down', 'waiting_back']);
});

it('goes to / when the reboot answers again', async () => {
    follow('reboot');
    up = false;
    await advance(4000);
    up = true;
    await advance(2000);

    expect(navigate).toHaveBeenCalledWith('/');
    expect(powerActionPending()).toBe(false);
});

it('warns after 3 minutes but keeps polling, so a late return still redirects', async () => {
    follow('reboot');
    up = false;
    await advance(180000 + 2000);

    expect(states).toEqual(['going_down', 'waiting_back', 'slow']);
    expect(navigate).not.toHaveBeenCalled();

    up = true;
    await advance(4000);
    expect(navigate).toHaveBeenCalledWith('/');
});

it('falls back after 30 s when the machine never went down', async () => {
    follow('reboot');
    await advance(30000);

    expect(states).toEqual(['going_down', 'not_down']);
    expect(powerActionPending()).toBe(false);
    const calls = fetchFn.mock.calls.length;
    await advance(10000);
    expect(fetchFn.mock.calls.length).toBe(calls);
});

it('does not fall back once the machine went down', async () => {
    follow('reboot');
    up = false;
    await advance(2000);
    await advance(60000);

    expect(states).not.toContain('not_down');
});

it('ends with "off" and stops polling when a shutdown went down', async () => {
    follow('shutdown');
    up = false;
    await advance(2000);

    expect(states).toEqual(['going_down', 'off']);
    expect(powerActionPending()).toBe(false);
    const calls = fetchFn.mock.calls.length;
    await advance(10000);
    expect(fetchFn.mock.calls.length).toBe(calls);
    expect(navigate).not.toHaveBeenCalled();
});

it('reports an action as pending while it is followed', async () => {
    expect(powerActionPending()).toBe(false);
    follow('reboot');
    expect(powerActionPending()).toBe(true);
});
