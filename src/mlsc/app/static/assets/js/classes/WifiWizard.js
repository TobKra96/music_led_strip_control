import { api } from './Api.js';
import { events } from './Events.js';
import Toast from './Toast.js';
import { ROLLBACK_SECONDS, addressOf, connectProblem, secondsLeft, signalLabel, wizardBlock, wizardResult } from './WifiView.js';

const STEPS = ['welcome', 'network', 'password', 'apply', 'result'];
const [WELCOME, NETWORK, PASSWORD, APPLY, RESULT] = STEPS.map((_, index) => index);
// Time to wait after the Rollback is due for the Operation event to arrive before the status is asked for.
const GRACE_SECONDS = 15;

/**
 * The Wi-Fi Setup Wizard: a modal that gets the Pi onto the home Wi-Fi, with the Wi-Fi Rollback as the safety net.
 */
export default class WifiWizard {
    /**
     * @param {{onClosed: function(boolean): void}} options `onClosed` runs when the wizard closes, with whether the user
     *   left before the Pi joined a network.
     */
    constructor({ onClosed }) {
        this.onClosed = onClosed;
        this.$modal = $('#modal_wifi_wizard');
        this.address = addressOf(window.location);
        this.step = WELCOME;
        this.networks = [];
        this.ssid = '';
        this.finished = false;
        this.startedAt = 0;
        this.timer = null;
        this._bind();
    }

    /**
     * Open the wizard on the welcome step, after the checks.
     * @param {object} status The body of `GET /api/v2/wifi/status`.
     */
    open(status) {
        this.finished = false;
        this.ssid = '';
        $('#wwz_ssid, #wwz_password').val('');
        const block = wizardBlock(status);
        $('#wwz_blocked').toggleClass('d-none', !block);
        $('#wwz_steps, .modal-footer', this.$modal).toggleClass('d-none', Boolean(block));
        if (block) {
            $('#wwz_block_text').text(block.text);
            $('#wwz_block_fix').text(block.fix || '');
            $('#wwz_radio_btn').toggleClass('d-none', !block.canEnableRadio);
        }
        $('#wwz_hotspot').toggleClass('d-none', !status.hotspot).text(status.hotspot ? `You are connected to ${status.hotspot.ssid}.` : '');
        this._goTo(WELCOME);
        this.$modal.modal('show');
    }

    _bind() {
        $('#wwz_next').on('click', () => this._next());
        $('#wwz_back').on('click', () => this._goTo(this.step === RESULT ? NETWORK : this.step - 1));
        $('#wwz_scan_btn').on('click', () => this._scan());
        $('#wwz_copy_btn').on('click', () => navigator.clipboard?.writeText(this.address).then(() => new Toast('Address copied.').success()));
        $('#wwz_radio_btn').on('click', () => api.put('/wifi/radio', { enabled: true })
            .then(() => api.get('/wifi/status'))
            .then(status => this.open(status))
            .catch(error => new Toast(`Could not turn Wi-Fi on. ${error.summary || ''}`).error()));
        $('#wwz_networks').on('click', 'button', (e) => {
            $('#wwz_ssid').val(e.currentTarget.dataset.ssid);
            this._next();
        });
        this.$modal.on('hidden.bs.modal', () => {
            clearInterval(this.timer);
            $('#wwz_password').val('');
            this.onClosed(!this.finished);
        });
        events.on('operation', event => this._onOperation(event));
    }

    _goTo(step) {
        this.step = step;
        $('.wifi-wizard-step').each((_, el) => $(el).toggleClass('d-none', el.getAttribute('data-step') !== STEPS[step]));
        $('#wwz_progress').text(step < APPLY ? `Step ${step + 1} of ${RESULT}` : '');
        $('#wwz_back').toggleClass('d-none', step === WELCOME || step === APPLY).text(step === RESULT ? 'Choose a network' : 'Back');
        $('#wwz_next').toggleClass('d-none', step === APPLY || step === RESULT).text(step === PASSWORD ? 'Connect' : 'Next');
        if (step === NETWORK) this._scan();
        if (step === PASSWORD) this._askForPassword();
    }

    async _next() {
        if (this.step === NETWORK) {
            this.ssid = $('#wwz_ssid').val().trim();
            const problem = connectProblem(this.ssid, '', []);
            if (problem) {
                new Toast(problem).warning();
                return;
            }
        }
        if (this.step === PASSWORD) {
            const problem = connectProblem(this.ssid, $('#wwz_password').val(), this.networks);
            if (problem) {
                new Toast(problem).warning();
                return;
            }
            await this._apply();
            return;
        }
        this._goTo(this.step + 1);
    }

    _askForPassword() {
        const network = this.networks.find(n => n.ssid === this.ssid);
        const open = Boolean(network) && !network.security;
        $('#wwz_password_ssid').text(this.ssid);
        $('#wwz_password_group').toggleClass('d-none', open);
        $('#wwz_open_hint').toggleClass('d-none', !open);
    }

    async _scan() {
        const $button = $('#wwz_scan_btn').prop('disabled', true);
        try {
            this.networks = (await api.get('/wifi/scan')).networks.sort((a, b) => b.signal - a.signal);
        } catch (error) {
            new Toast(`Could not scan for networks. ${error.summary || ''}`).error();
        } finally {
            $button.prop('disabled', false);
        }
        const $list = $('#wwz_networks').empty();
        this.networks.forEach((network) => {
            const meta = [signalLabel(network.signal), network.security ? 'secured' : 'open'].join(' · ');
            $list.append($('<button type="button" class="list-group-item list-group-item-action"></button>')
                .attr('data-ssid', network.ssid).text(network.ssid).append($('<small class="text-muted ml-2"></small>').text(meta)));
        });
        $('#wwz_scan_empty').toggleClass('d-none', this.networks.length > 0);
    }

    async _apply() {
        const password = $('#wwz_password').val();
        $('#wwz_password').val('');
        this.startedAt = Date.now();
        this._goTo(APPLY);
        this._tick();
        clearInterval(this.timer);
        this.timer = setInterval(() => this._tick(), 1000);
        try {
            await api.post('/wifi/connect', { ssid: this.ssid, password: password || null });
        } catch (error) {
            // Status 0: the Pi left the Hotspot, so this page lost its connection. The Operation decides how it ended.
            if (error.status !== 0) this._finish({ state: 'failed', error: error.message });
        }
    }

    _tick() {
        $('#wwz_countdown').text(secondsLeft(this.startedAt, Date.now()));
        if (this.step === APPLY && Date.now() - this.startedAt > (ROLLBACK_SECONDS + GRACE_SECONDS) * 1000) this._checkStatus();
    }

    async _checkStatus() {
        try {
            const status = await api.get('/wifi/status');
            this._finish({ state: status.connected && status.ssid === this.ssid ? 'confirmed' : 'rolled_back', error: null });
        } catch {
            // The Pi is not reachable from here yet: try again on the next tick.
        }
    }

    _onOperation(event) {
        if (event.kind === 'wifi' && this.step === APPLY && event.state !== 'pending') this._finish(event);
    }

    _finish(operation) {
        clearInterval(this.timer);
        const result = wizardResult(operation, this.ssid, this.address);
        this.finished = result.success;
        $('#wwz_result').removeClass('alert-success alert-danger').addClass(result.success ? 'alert-success' : 'alert-danger').text(result.text);
        $('#wwz_address_row').toggleClass('d-none', !result.success);
        $('#wwz_address').text(this.address);
        this._goTo(RESULT);
        $('#wwz_back').toggleClass('d-none', result.success);
    }
}
