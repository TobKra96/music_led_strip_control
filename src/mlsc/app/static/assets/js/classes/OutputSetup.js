/** Pure helpers of the Setup Wizard: what it sends to the API and what it tells the user about power and speed. */

const FPS_NUMERATOR = 25600;
const DEFAULT_VOLTS = 5;
const SPLIT_FROM_LEDS = 600;

/**
 * @typedef {object} WizardState
 * @property {string} output_type `output_raspi`, `output_udp` or `output_dummy`.
 * @property {number} led_pin
 * @property {number} led_dma
 * @property {number} led_freq_hz
 * @property {boolean} led_invert
 * @property {string} udp_client_ip
 * @property {number} udp_client_port
 * @property {string} chip_family
 * @property {boolean} white_channel
 * @property {string} colour_order
 * @property {number} led_count
 * @property {number} led_mid
 * @property {number} led_brightness
 * @property {boolean} power_enabled
 * @property {number} supply_volts
 * @property {number} supply_amps
 * @property {number} ma_per_led
 */

/**
 * The body of `PATCH /devices/<id>/output` for the state of the wizard. Only the settings of the chosen output type are sent.
 * @param {WizardState} state
 * @return {object}
 */
export const outputPatch = (state) => {
    const output = {};
    if (state.output_type === 'output_raspi') {
        output.output_raspi = {
            led_pin: state.led_pin, led_dma: state.led_dma, led_freq_hz: state.led_freq_hz, led_invert: state.led_invert,
        };
    } else if (state.output_type === 'output_udp') {
        output.output_udp = { udp_client_ip: state.udp_client_ip, udp_client_port: state.udp_client_port };
    }
    return {
        output_type: state.output_type,
        chip_family: state.chip_family,
        white_channel: state.chip_family === 'sk6812' && state.white_channel,
        colour_order: state.colour_order,
        led_count: state.led_count,
        led_mid: Math.min(state.led_mid, Math.max(state.led_count - 1, 0)),
        power_limit: {
            enabled: state.power_enabled, supply_volts: state.supply_volts, supply_amps: state.supply_amps, ma_per_led: state.ma_per_led, mode: 'warn',
        },
        output,
    };
};

/**
 * The wizard state of the stored settings of a device.
 * @param {object} settings The settings of the device, as returned by `GET /devices/<id>/settings`.
 * @return {WizardState}
 */
export const stateFrom = (settings) => {
    const raspi = settings.output.output_raspi;
    const udp = settings.output.output_udp;
    const limit = settings.power_limit;
    return {
        output_type: settings.output_type,
        led_pin: raspi.led_pin,
        led_dma: raspi.led_dma,
        led_freq_hz: raspi.led_freq_hz,
        led_invert: raspi.led_invert,
        udp_client_ip: udp.udp_client_ip,
        udp_client_port: udp.udp_client_port,
        chip_family: settings.chip_family,
        white_channel: settings.white_channel,
        colour_order: settings.colour_order,
        led_count: settings.led_count,
        led_mid: settings.led_mid,
        led_brightness: settings.led_brightness,
        power_enabled: limit.enabled,
        supply_volts: limit.supply_volts ?? DEFAULT_VOLTS,
        supply_amps: limit.supply_amps,
        ma_per_led: limit.ma_per_led,
    };
};

/**
 * What the strip can draw at full white and the brightness it runs at, and the warning the Power Limit gives. Advisory: nothing is dimmed.
 * @param {WizardState} state
 * @return {{amps: number, watts: number, warning: string|null}}
 */
export const powerEstimate = (state) => {
    const amps = state.led_count * state.ma_per_led / 1000 * state.led_brightness / 100;
    const warning = state.power_enabled && amps > state.supply_amps
        ? `The strip can draw ${amps.toFixed(1)} A at full white, more than the ${state.supply_amps.toFixed(1)} A supply. `
            + 'Lower the brightness, use a bigger supply or split the strip.'
        : null;
    return { amps, watts: amps * state.supply_volts, warning };
};

/**
 * The frame rate a strip of this length can reach, and the advice for a long one.
 * @param {number} ledCount
 * @return {{fps: number|null, suggestion: string|null}}
 */
export const speedEstimate = (ledCount) => {
    if (ledCount < 1) return { fps: null, suggestion: null };
    const fps = Math.floor(FPS_NUMERATOR / ledCount);
    const suggestion = ledCount >= SPLIT_FROM_LEDS
        ? `${ledCount} LEDs limit the strip to about ${fps} fps. Split it into several Devices on separate pins for a higher frame rate.`
        : null;
    return { fps, suggestion };
};

/**
 * The name and groups that differ from the stored settings, for `PATCH /devices/<id>/settings`.
 * @param {{device_name: string, device_groups: Object.<string, string>}} settings
 * @param {string} name
 * @param {Object.<string, string>} groups Group id to group name.
 * @return {object} Empty when nothing changed.
 */
export const identityPatch = (settings, name, groups) => {
    const patch = {};
    if (name !== settings.device_name) patch.device_name = name;
    const stored = Object.keys(settings.device_groups).sort();
    const chosen = Object.keys(groups).sort();
    if (stored.length !== chosen.length || stored.some((id, i) => id !== chosen[i])) patch.device_groups = groups;
    return patch;
};

/**
 * The settings of the flat form that the safe apply handles: the rest is saved as before.
 */
export const OUTPUT_FIELDS = ['output_type', 'led_count', 'led_mid', 'led_brightness', 'chip_family', 'colour_order', 'white_channel'];

/**
 * Split the serialized flat form into what goes through the safe apply and what is saved directly.
 * @param {object} form
 * @param {object} output The `output` object of the form.
 * @return {{apply: object, save: object}}
 */
export const splitForm = (form, output) => {
    const apply = { output };
    const save = {};
    Object.entries(form).forEach(([key, value]) => {
        (OUTPUT_FIELDS.includes(key) ? apply : save)[key] = value;
    });
    return { apply, save };
};
