/** The audio sources the Microphone page offers, by the `source` the settings and the audio status carry. */
export const SOURCES = { device: 'Server device', browser: 'This browser' };

/** Offered as sample rates for the browser, which has no device to ask. The server resamples to the one picked. */
export const BROWSER_SAMPLE_RATES = [16000, 22050, 32000, 44100, 48000];

/** The rate the effects run at when none is picked, as the server's `DEFAULT_SAMPLE_RATE`. */
export const BROWSER_NATIVE_RATE = 44100;

/**
 * Which parts of the page belong to a source: the Device dropdown to a server device, the stream button to this browser.
 * @param {string} source
 * @return {{device: boolean, browser: boolean}}
 */
export const sectionsFor = source => ({ device: source !== 'browser', browser: source === 'browser' });

/**
 * What MLSC listens to, for the line that is shown at all times. Based on the saved settings, so it also tells
 * when this browser is selected but not streaming yet.
 * @param {{source: string, device_name: string|null}} settings
 * @param {{state?: string, device?: string}|null} status the latest audio status, if one arrived
 * @return {string}
 */
export const listeningTo = (settings, status) => {
    if (settings.source === 'browser') {
        return status && status.state === 'ok' ? 'Listening to: this browser' : 'Listening to: this browser (not streaming yet)';
    }
    if (status && status.state === 'error') return 'Listening to: nothing, the device does not work';
    if (status && status.device && ['ok', 'starting'].includes(status.state)) return `Listening to: ${status.device}`;
    return `Listening to: ${settings.device_name || 'the system default device'}`;
};
