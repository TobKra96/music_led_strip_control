import PowerFollower from './PowerFollower.js';

const ACTIONS = {
    reboot: {
        label: 'Reboot',
        buttonClass: 'btn-warning',
        question: 'Reboot this machine?',
        body: 'The LED strips go dark until it is back up, which takes a minute or two.',
        logsNote: ' Server logs may be cleared.',
        progress: 'Rebooting…',
    },
    shutdown: {
        label: 'Shut down',
        buttonClass: 'btn-danger',
        question: 'Shut down this machine?',
        body: 'The LED strips go dark and the machine must be switched on by hand afterwards.',
        logsNote: '',
        progress: 'Shutting down…',
    },
};

/**
 * The Power card of the System Status page: Reboot and Shut down, each behind a confirmation.
 * It renders all of its own markup into `root`.
 */
export default class PowerCard {
    /**
     * @param {HTMLElement} root Element the card is rendered into.
     * @param {{get: function(string): Promise.<any>, post: function(string): Promise.<any>}} api
     * @param {{logsClearedOnReboot?: boolean, follower?: object}} [options] `logsClearedOnReboot` is `false` when the
     *   journal survives a reboot; `follower` overrides the options of the PowerFollower (timings, navigation).
     */
    constructor(root, api, { logsClearedOnReboot = true, follower = {} } = {}) {
        this.root = root;
        this.followerOptions = follower;
        this.api = api;
        this.logsClearedOnReboot = logsClearedOnReboot;
        this.pending = null;
        this.busy = false;
        this.render();
        this.showError(null);
    }

    /** Read which actions the host allows and enable the buttons accordingly. */
    load() {
        return this.api.get('/system/power').then((capabilities) => {
            const warning = this.el('[data-power-autostart]');
            warning.textContent = capabilities.autostart_warning || '';
            warning.hidden = !capabilities.autostart_warning;
            Object.keys(ACTIONS).forEach((action) => {
                const { available, reason } = capabilities[action] || { available: false, reason: 'Unknown.' };
                this.button(action).disabled = !available;
                this.reasonOf(action).textContent = available ? '' : (reason || '');
            });
        }).catch((error) => {
            Object.keys(ACTIONS).forEach((action) => {
                this.reasonOf(action).textContent = error.message || 'Unable to reach the server.';
            });
        });
    }

    /** @param {string} selector */
    el(selector) {
        return this.root.querySelector(selector);
    }

    button(action) {
        return this.el(`[data-power-action="${action}"]`);
    }

    reasonOf(action) {
        return this.el(`[data-power-reason="${action}"]`);
    }

    render() {
        const actions = Object.entries(ACTIONS).map(([action, { label, buttonClass }]) => `
            <div class="mlsc-power-action">
                <button type="button" class="btn ${buttonClass} m-0" data-power-action="${action}" disabled>${label}</button>
                <small class="d-block text-muted mt-1" data-power-reason="${action}"></small>
            </div>`).join('');

        this.root.innerHTML = `
            <div class="card p-0" data-power-card>
                <div class="card-header">
                    <h5><i class="feather icon-power text-c-blue"></i> Power</h5>
                </div>
                <div class="card-block">
                    <div class="d-flex flex-wrap mlsc-power-actions">${actions}</div>
                    <div class="alert alert-warning mb-0 mt-3" role="alert" data-power-autostart hidden></div>
                </div>
                <div class="card-block pt-0" data-power-error-block></div>
            </div>
            <div class="mlsc-power-modal" data-power-modal role="dialog" aria-modal="true" aria-labelledby="power_modal_title" hidden>
                <div class="card mlsc-power-dialog p-4">
                    <h5 id="power_modal_title" data-power-title></h5>
                    <p class="mb-4" data-power-body></p>
                    <div class="d-flex flex-column-reverse flex-md-row justify-content-md-end">
                        <button type="button" class="btn btn-secondary m-0 mt-2 mt-md-0" data-power-cancel>Cancel</button>
                        <button type="button" class="btn btn-danger m-0 ml-md-3" data-power-confirm>Confirm</button>
                    </div>
                </div>
            </div>`;

        Object.keys(ACTIONS).forEach((action) => {
            this.button(action).addEventListener('click', () => this.ask(action));
        });
        this.el('[data-power-cancel]').addEventListener('click', () => this.close());
        this.el('[data-power-confirm]').addEventListener('click', () => this.confirm());
        const modal = this.el('[data-power-modal]');
        modal.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.close();
            if (e.key === 'Tab') this.trapFocus(e);
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.close();
        });
    }

    /** @param {string} action */
    ask(action) {
        const { question, body, logsNote } = ACTIONS[action];
        this.pending = action;
        this.showError(null);
        this.el('[data-power-title]').textContent = question;
        this.el('[data-power-body]').textContent = body + (this.logsClearedOnReboot ? logsNote : '');
        this.el('[data-power-confirm]').textContent = ACTIONS[action].label;
        this.el('[data-power-modal]').hidden = false;
        this.el('[data-power-cancel]').focus();
    }

    /** Keep Tab inside the dialog while it is open. */
    trapFocus(e) {
        const cancel = this.el('[data-power-cancel]');
        const confirm = this.el('[data-power-confirm]');
        const [first, last] = [cancel, confirm];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    }

    close() {
        if (this.busy) return;
        const action = this.pending;
        this.pending = null;
        this.el('[data-power-modal]').hidden = true;
        if (action && this.button(action)) this.button(action).focus();
    }

    confirm() {
        const action = this.pending;
        if (!action || this.busy) return;
        this.busy = true;
        this.el('[data-power-confirm]').disabled = true;
        this.api.post(`/system/${action}`).then(
            () => this.goingDown(action),
            (error) => {
                // A dropped connection right after the click means the machine is probably already going down.
                if (error.status === 0) {
                    this.goingDown(action);
                } else {
                    this.busy = false;
                    this.close();
                    this.showError(error.message);
                }
            },
        );
    }

    /**
     * Replace the card with a banner and follow the machine until it is back, or off.
     * @param {string} action
     */
    goingDown(action) {
        this.pending = null;
        const { progress } = ACTIONS[action];
        const texts = {
            going_down: { level: 'info', text: progress },
            waiting_back: { level: 'info', text: 'Waiting for the machine to come back�' },
            slow: {
                level: 'warning',
                text: 'The machine has not come back yet. It may still be starting; this page keeps checking.',
                reload: true,
            },
            off: { level: 'info', text: 'The machine is off. Switch it on by hand to use MLSC again.' },
        };
        new PowerFollower(action, (state) => {
            if (state === 'not_down') {
                this.render();
                this.showError('The machine did not seem to go down.');
                this.busy = false;
                this.load();
                return;
            }
            this.showBanner(texts[state]);
        }, this.followerOptions).start();
    }

    /** @param {{level: string, text: string, reload?: boolean}} banner */
    showBanner({ level, text, reload = false }) {
        this.root.innerHTML = `
            <div class="alert alert-${level} mlsc-banner" role="status" data-power-banner>
                <i class="feather icon-info mr-2" aria-hidden="true"></i><strong></strong>
            </div>`;
        const banner = this.el('[data-power-banner]');
        this.el('[data-power-banner] strong').textContent = text;
        if (reload) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'btn btn-sm btn-outline-secondary ml-3';
            button.setAttribute('data-power-reload', '');
            button.textContent = 'Reload';
            button.addEventListener('click', () => window.location.reload());
            banner.append(button);
        }
    }

    /** @param {string|null} message */
    showError(message) {
        const block = this.el('[data-power-error-block]');
        block.replaceChildren();
        block.hidden = !message;
        if (!message) return;
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger mb-0';
        alert.setAttribute('role', 'alert');
        alert.setAttribute('data-power-error', '');
        alert.textContent = message;
        block.append(alert);
    }
}
