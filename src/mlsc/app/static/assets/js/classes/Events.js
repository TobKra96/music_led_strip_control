import { redirectToLogin } from './Login.js';

const EVENTS_URL = '/api/v2/events';
const SESSION_URL = '/api/v2/auth/session';
const RETRY_MS = 5000;
// Raised by this class itself, not by the server.
const LOCAL_EVENTS = ['ready', 'disconnected'];

/**
 * The one server-sent event stream of the page. The browser reconnects on its own after a network error
 * and sends `Last-Event-ID`; only a refused connection (`401`, `503`) closes the stream, so that one is retried here,
 * unless the session has ended: then the browser goes to the login page.
 */
class EventStream {
    constructor() {
        /** @type {Map.<string, Array.<function(any): void>>} */
        this._handlers = new Map();
        /** @type {EventSource|null} */
        this._source = null;
        this._retryTimer = null;
    }

    /**
     * Listen for an event. `ready` fires whenever the stream is (re)connected, `disconnected` when it is lost.
     * @param {string} event e.g. `device.status`, `system.stats`, `diagnosis`, `operation`, `ready`, `disconnected`.
     * @param {function(any): void} handler Gets the parsed `data` of the event.
     */
    on(event, handler) {
        const known = this._handlers.has(event);
        this._handlers.set(event, [...(this._handlers.get(event) || []), handler]);
        // One DOM listener per event name fans out to all handlers; the ones registered before `connect` are added there.
        if (this._source && !known) this._listen(event);
    }

    _listen(event) {
        if (!LOCAL_EVENTS.includes(event)) {
            this._source.addEventListener(event, e => this._deliver(event, e.data));
        }
    }

    /** Open the stream once; later calls do nothing. */
    connect() {
        if (this._source) return;
        this._source = new EventSource(EVENTS_URL);

        this._source.addEventListener('ready', () => this._emit('ready'));
        for (const event of this._handlers.keys()) this._listen(event);

        this._source.onerror = () => {
            this._emit('disconnected');
            if (this._source.readyState === EventSource.CLOSED) {
                this._source = null;
                this._retryUnlessLoggedOut();
            }
        };
    }

    /**
     * `EventSource` does not expose the status of a refused connection, so ask the session endpoint whether it was a `401`.
     * An unreachable server counts as not logged out.
     */
    async _retryUnlessLoggedOut() {
        clearTimeout(this._retryTimer);
        try {
            const response = await fetch(SESSION_URL, { headers: { Accept: 'application/json' }, credentials: 'same-origin' });
            const session = await response.json();
            if (session.pin_required && !session.authenticated) {
                redirectToLogin();
                return;
            }
        } catch (e) {
            // Server restarting or unreachable: retry below.
        }
        clearTimeout(this._retryTimer);
        this._retryTimer = setTimeout(() => this.connect(), RETRY_MS);
    }

    _deliver(event, raw) {
        try {
            this._emit(event, JSON.parse(raw));
        } catch (e) {
            console.error(`Invalid '${event}' event`, e);
        }
    }

    _emit(event, data) {
        (this._handlers.get(event) || []).forEach(handler => handler(data));
    }
}

export const events = new EventStream();
