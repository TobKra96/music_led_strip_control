const DEFAULT_INTERVAL_MS = 5000;
const VOLATILE_NOTE = 'Logs are kept in memory and are cleared when the machine restarts.';

const LEVELS = [['', 'All'], ['info', 'INFO'], ['warning', 'WARNING'], ['error', 'ERROR']];
const LINE_COUNTS = [100, 200, 500, 1000];
const DEFAULT_LINES = 200;

/**
 * The Server logs card of the System Status page: a filterable view of the logs of the current boot.
 * It renders all of its own markup into `root`.
 */
export default class LogsCard {
    /**
     * @param {HTMLElement} root Element the card is rendered into.
     * @param {{get: function(string): Promise.<any>}} api
     * @param {{intervalMs?: number}} [options] `intervalMs` is the auto-refresh period.
     */
    constructor(root, api, { intervalMs = DEFAULT_INTERVAL_MS } = {}) {
        this.root = root;
        this.api = api;
        this.intervalMs = intervalMs;
        this.expanded = true;
        this.timer = null;
        this.requestId = 0;
        this.render();
        document.addEventListener('visibilitychange', () => this.syncTimer());
    }

    /** Fetch the logs with the toolbar values and show them. */
    load() {
        const id = ++this.requestId;
        return this.api.get(`/system/logs?${this.params()}`).then(
            (logs) => { if (id === this.requestId) this.show(logs); },
            (error) => { if (id === this.requestId) this.showError(error.message); },
        );
    }

    /** @return {string} */
    params() {
        const params = new URLSearchParams({ lines: this.el('[data-logs-lines]').value });
        const level = this.el('[data-logs-level-select]').value;
        const text = this.el('[data-logs-filter]').value.trim();
        if (level) params.set('level', level);
        if (text) params.set('q', text);
        return params.toString();
    }

    /** @param {string} selector */
    el(selector) {
        return this.root.querySelector(selector);
    }

    render() {
        const levels = LEVELS.map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
        const counts = LINE_COUNTS.map((n) => `<option value="${n}"${n === DEFAULT_LINES ? ' selected' : ''}>${n}</option>`).join('');

        this.root.innerHTML = `
            <div class="accordion">
                <div class="card p-0" data-logs-card>
                    <div class="card-header" data-logs-toggle role="button" tabindex="0" aria-expanded="true">
                        <h5><i class="feather icon-file-text text-c-blue"></i> Server logs</h5>
                        <i class="fa-solid fa-chevron-down text-c-blue float-right mt-1"></i>
                    </div>
                    <div class="card-body p-0" data-logs-body>
                        <div class="card-block">
                            <div class="mlsc-logs-toolbar">
                                <input type="search" class="form-control" placeholder="Filter" aria-label="Filter text" data-logs-filter maxlength="200">
                                <select class="form-control" aria-label="Level" data-logs-level-select>${levels}</select>
                                <select class="form-control" aria-label="Lines" data-logs-lines>${counts}</select>
                                <button type="button" class="btn btn-primary m-0" data-logs-refresh>Refresh</button>
                                <label class="m-0 d-flex align-items-center"><input type="checkbox" class="mr-2" data-logs-auto> Auto-refresh</label>
                            </div>
                            <small class="d-block text-muted mb-2" data-logs-volatile hidden>${VOLATILE_NOTE}</small>
                            <div class="alert alert-danger mb-2" role="alert" data-logs-error hidden></div>
                            <div class="text-muted" data-logs-unavailable hidden></div>
                            <div class="mlsc-logs-pane" data-logs-pane tabindex="0">
                                <div class="mlsc-logs-empty" data-logs-empty hidden>No matching lines</div>
                                <div data-logs-lines-list></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;

        const toggle = this.el('[data-logs-toggle]');
        toggle.addEventListener('click', () => this.setExpanded(!this.expanded));
        toggle.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                this.setExpanded(!this.expanded);
            }
        });
        this.el('[data-logs-refresh]').addEventListener('click', () => this.load());
        this.el('[data-logs-filter]').addEventListener('keydown', (event) => {
            if (event.key === 'Enter') this.load();
        });
        this.el('[data-logs-level-select]').addEventListener('change', () => this.load());
        this.el('[data-logs-lines]').addEventListener('change', () => this.load());
        this.el('[data-logs-auto]').addEventListener('change', () => this.syncTimer());
    }

    /** @param {boolean} expanded */
    setExpanded(expanded) {
        this.expanded = expanded;
        this.el('[data-logs-body]').hidden = !expanded;
        this.el('[data-logs-toggle]').setAttribute('aria-expanded', String(expanded));
        this.syncTimer();
        if (expanded) this.scrollToEnd();
    }

    /** Auto-refresh only runs while it is ticked, the card is open and the page is visible. */
    syncTimer() {
        const active = this.el('[data-logs-auto]').checked && this.expanded && !document.hidden;
        if (active && this.timer === null) {
            this.timer = setInterval(() => this.load(), this.intervalMs);
        } else if (!active && this.timer !== null) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    scrollToEnd() {
        const pane = this.el('[data-logs-pane]');
        pane.scrollTop = pane.scrollHeight;
    }

    /** @param {{unavailable: string|null, persistent: boolean|null, entries: Array.<object>}} logs */
    show(logs) {
        this.showError(null);
        const unavailable = this.el('[data-logs-unavailable]');
        unavailable.hidden = !logs.unavailable;
        unavailable.textContent = logs.unavailable || '';
        this.el('[data-logs-pane]').hidden = !!logs.unavailable;
        this.el('[data-logs-volatile]').hidden = logs.unavailable || logs.persistent !== false;

        const list = this.el('[data-logs-lines-list]');
        list.replaceChildren(...logs.entries.map((entry) => this.line(entry)));
        this.el('[data-logs-empty]').hidden = !!logs.unavailable || logs.entries.length > 0;
        this.scrollToEnd();
    }

    /** @param {{time: string|null, level: string|null, message: string}} entry */
    line(entry) {
        const line = document.createElement('div');
        line.className = 'mlsc-logs-line';
        line.setAttribute('data-logs-line', '');

        const time = document.createElement('span');
        time.className = 'mlsc-logs-time';
        time.setAttribute('data-logs-time', '');
        time.textContent = formatTime(entry.time);

        const level = document.createElement('span');
        level.className = `mlsc-logs-level mlsc-logs-level-${entry.level || 'none'}`;
        level.setAttribute('data-logs-level', '');
        level.textContent = entry.level ? entry.level.toUpperCase() : '';

        const message = document.createElement('span');
        message.className = 'mlsc-logs-message';
        message.setAttribute('data-logs-message', '');
        message.textContent = entry.message;

        line.append(time, level, message);
        return line;
    }

    /** @param {string|null} message */
    showError(message) {
        const error = this.el('[data-logs-error]');
        error.hidden = !message;
        error.textContent = message || '';
    }
}

/** @param {string|null} iso */
function formatTime(iso) {
    if (!iso) return '';
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? iso : date.toLocaleTimeString([], { hour12: false });
}
