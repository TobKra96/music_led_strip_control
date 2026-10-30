import { api } from './Api.js';
import { waitForOperation } from './Operation.js';
import { outputPatch, powerEstimate, speedEstimate, stateFrom } from './OutputSetup.js';
import Toast from './Toast.js';

const STEPS = ['output', 'strip', 'leds', 'power', 'review'];
const NUMBER_FIELDS = ['led_pin', 'led_dma', 'led_freq_hz', 'udp_client_port', 'led_count', 'led_mid', 'supply_volts', 'supply_amps', 'ma_per_led'];
const TEXT_FIELDS = ['output_type', 'udp_client_ip', 'chip_family', 'colour_order'];
const CHECKBOX_FIELDS = ['led_invert', 'white_channel', 'power_enabled'];

/**
 * The per-Device Setup Wizard: a modal that walks through the Output, the strip, the LED count and the Power Limit,
 * and applies the result with the safe apply of `PATCH /devices/<id>/output`.
 */
export default class SetupWizard {
    /**
     * @param {{getOutputTypes: function(): Object.<string, string>, onApplied: function(): void}} options
     *   `getOutputTypes` is read when the wizard opens, since the page loads the types after it creates the wizard.
     *   `onApplied` runs after a confirmed apply, so the page can reload the settings.
     */
    constructor({ getOutputTypes, onApplied }) {
        this.getOutputTypes = getOutputTypes;
        this.onApplied = onApplied;
        this.$modal = $('#modal_wizard');
        this.step = 0;
        this.deviceId = null;
        this.state = null;
        this.options = null;
        this._bind();
    }

    /**
     * Open the wizard for a device, filled from its stored settings.
     * @param {string} deviceId
     * @return {Promise}
     */
    async open(deviceId) {
        this.deviceId = deviceId;
        const [settings, options] = await Promise.all([
            api.get(`/devices/${deviceId}/settings`), api.get(`/devices/${deviceId}/output/setup`),
        ]);
        this.state = stateFrom(settings);
        this.options = options;
        this._fill();
        this.step = 0;
        $('#wz_result').addClass('d-none');
        this._show();
        this.$modal.modal('show');
    }

    _bind() {
        $('#wz_next').on('click', () => this._next());
        $('#wz_back').on('click', () => { this.step -= 1; this._show(); });
        $('#wz_advanced_toggle').on('click', (e) => { e.preventDefault(); $('#wz_advanced').toggleClass('d-none'); });
        const fields = [...NUMBER_FIELDS, ...TEXT_FIELDS, ...CHECKBOX_FIELDS].map(key => `#wz_${key}`).join(',');
        $(fields).on('input change', () => { this._read(); this._refresh(); });
        $('#wz_test_colours').on('click', () => this._applyAndShow('colour_order'));
        $('#wz_test_markers').on('click', () => this._applyAndShow('markers'));
        $('#wz_test_chase').on('click', () => this._showPattern('chase'));
        $('#wz_test_power').on('click', () => this._showPattern('power'));
    }

    _fill() {
        const $type = $('#wz_output_type').empty();
        Object.entries(this.getOutputTypes()).forEach(([key, name]) => $type.append($('<option></option>').val(key).text(name)));
        const $pin = $('#wz_led_pin').empty();
        Object.keys(this.options.pin_channels).forEach((pin) => {
            $pin.append($('<option></option>').val(pin).text(`GPIO ${pin} (channel ${this.options.pin_channels[pin]})`));
        });
        $('#wz_led_pin').closest('.form-group').toggleClass('d-none', !$pin.children().length);
        $('#wizard_notice').toggleClass('d-none', !this.options.experimental).text(this.options.experimental || '');
        NUMBER_FIELDS.concat(TEXT_FIELDS).forEach(key => $(`#wz_${key}`).val(this.state[key]));
        CHECKBOX_FIELDS.forEach(key => $(`#wz_${key}`).prop('checked', this.state[key]));
        this._refresh();
    }

    _read() {
        NUMBER_FIELDS.forEach((key) => {
            const value = $(`#wz_${key}`).val();
            if (value !== '' && value !== null) this.state[key] = Number(value);
        });
        TEXT_FIELDS.forEach((key) => { this.state[key] = $(`#wz_${key}`).val(); });
        CHECKBOX_FIELDS.forEach((key) => { this.state[key] = $(`#wz_${key}`).prop('checked'); });
    }

    _refresh() {
        const type = this.state.output_type;
        $('#wz_gpio').toggleClass('d-none', type !== 'output_raspi');
        $('#wz_udp').toggleClass('d-none', type !== 'output_udp');
        $('#wz_mock').toggleClass('d-none', type !== 'output_dummy');
        $('#wz_white_row').toggleClass('d-none', this.state.chip_family !== 'sk6812');

        const { fps, suggestion } = speedEstimate(this.state.led_count);
        $('#wz_speed').text(fps ? `Expected maximum: about ${fps} fps for ${this.state.led_count} LEDs.` : '');
        $('#wz_split').toggleClass('d-none', !suggestion).text(suggestion || '');

        const power = powerEstimate(this.state);
        $('#wz_draw').text(`Estimated draw at full white and ${this.state.led_brightness}% brightness: ${power.amps.toFixed(1)} A, ${power.watts.toFixed(0)} W.`);
        $('#wz_power_warning').toggleClass('d-none', !power.warning).text(power.warning || '');
        $('#wz_summary').text(JSON.stringify(outputPatch(this.state), null, 2));
    }

    _show() {
        $('.wizard-step').each((_, el) => $(el).toggleClass('d-none', el.getAttribute('data-step') !== STEPS[this.step]));
        $('#wizard_progress').text(`Step ${this.step + 1} of ${STEPS.length}`);
        $('#wz_back').toggleClass('d-none', this.step === 0);
        $('#wz_next').text(this.step === STEPS.length - 1 ? 'Apply' : 'Next');
        this._refresh();
    }

    async _next() {
        this._read();
        if (this.step < STEPS.length - 1) {
            this.step += 1;
            this._show();
            return;
        }
        if (await this._apply()) this.$modal.modal('hide');
    }

    /**
     * Apply the wizard state as an Operation and tell how it ended.
     * @return {Promise.<boolean>} Whether the apply was confirmed.
     */
    async _apply() {
        const $result = $('#wz_result').removeClass('d-none alert-success alert-danger').addClass('alert-info').text('Applying…');
        try {
            const operation = await waitForOperation(await api.patch(`/devices/${this.deviceId}/output`, outputPatch(this.state)));
            const confirmed = operation.state === 'confirmed';
            $result.removeClass('alert-info').addClass(confirmed ? 'alert-success' : 'alert-danger')
                .text(confirmed
                    ? 'Applied. The strip shows the markers for a moment.'
                    : `It did not work and the previous settings are back. ${operation.error || ''}`);
            if (confirmed) this.onApplied();
            return confirmed;
        } catch (error) {
            $result.removeClass('alert-info').addClass('alert-danger');
            $result.text(error.errors?.length ? error.errors.map(e => `${e.field}: ${e.detail}`).join(' ') : error.message);
            return false;
        }
    }

    async _applyAndShow(pattern) {
        this._read();
        if (await this._apply()) await this._showPattern(pattern);
    }

    async _showPattern(pattern) {
        try {
            await api.post(`/devices/${this.deviceId}/test-pattern`, { pattern, duration_seconds: 20 });
        } catch (error) {
            new Toast(`Could not show the test pattern. ${error.summary || ''}`).error();
        }
    }
}
