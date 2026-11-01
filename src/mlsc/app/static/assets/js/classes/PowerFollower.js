const SESSION_URL = '/api/v2/auth/session';

/** Tunable timings, in milliseconds. */
export const POLL_INTERVAL_MS = 2000;
export const DOWN_TIMEOUT_MS = 30000;
export const BACK_TIMEOUT_MS = 180000;

let followers = 0;

/** True while a Power Action is being followed; the generic Connection-lost banner stays quiet then. */
export const powerActionPending = () => followers > 0;

/**
 * Follows an accepted Power Action in the browser by polling the session endpoint, ignoring the event stream.
 * Phase 1 waits for the first failed request (the machine is down). For a reboot, phase 2 waits for the first
 * success (it is back) and then navigates to `/`. The server still answering right after the `202` is therefore
 * never taken for a return.
 *
 * `onState` receives one of: `going_down`, `waiting_back`, `slow` (reboot not back in time, polling goes on quietly),
 * `not_down` (never seen going down), `off` (shutdown done).
 */
export default class PowerFollower {
    /**
     * @param {'reboot'|'shutdown'} action
     * @param {function(string): void} onState
     * @param {{navigate?: function(string): void, fetchFn?: function, intervalMs?: number, downTimeoutMs?: number, backTimeoutMs?: number}} [options]
     */
    constructor(action, onState, {
        navigate = (url) => window.location.assign(url),
        fetchFn = (...args) => fetch(...args),
        intervalMs = POLL_INTERVAL_MS,
        downTimeoutMs = DOWN_TIMEOUT_MS,
        backTimeoutMs = BACK_TIMEOUT_MS,
    } = {}) {
        this.action = action;
        this.onState = onState;
        this.navigate = navigate;
        this.fetchFn = fetchFn;
        this.intervalMs = intervalMs;
        this.downTimeoutMs = downTimeoutMs;
        this.backTimeoutMs = backTimeoutMs;
        this.running = false;
        this.down = false;
        this.timer = null;
        this.deadline = null;
    }

    start() {
        this.running = true;
        followers += 1;
        this.onState('going_down');
        this.deadline = setTimeout(() => this.downTimedOut(), this.downTimeoutMs);
        this.poll();
    }

    stop() {
        if (!this.running) return;
        this.running = false;
        followers -= 1;
        clearTimeout(this.timer);
        clearTimeout(this.deadline);
    }

    downTimedOut() {
        if (this.down) return;
        this.stop();
        this.onState('not_down');
    }

    /** @return {Promise.<boolean>} Whether the server answered. */
    async probe() {
        const controller = new AbortController();
        const abort = setTimeout(() => controller.abort(), this.intervalMs);
        try {
            const response = await this.fetchFn(SESSION_URL, { credentials: 'same-origin', cache: 'no-store', signal: controller.signal });
            return response.ok;
        } catch {
            return false;
        } finally {
            clearTimeout(abort);
        }
    }

    async poll() {
        const up = await this.probe();
        if (!this.running) return;

        if (!this.down) {
            if (!up) this.wentDown();
            if (!this.running) return;
        } else if (up) {
            this.stop();
            this.navigate('/');
            return;
        }
        this.timer = setTimeout(() => this.poll(), this.intervalMs);
    }

    wentDown() {
        this.down = true;
        clearTimeout(this.deadline);
        if (this.action === 'shutdown') {
            this.stop();
            this.onState('off');
            return;
        }
        this.onState('waiting_back');
        this.deadline = setTimeout(() => this.onState('slow'), this.backTimeoutMs);
    }
}
