/** How long a Wi-Fi change has to prove itself before the server rolls it back, as the server's `ROLLBACK_SECONDS`. */
export const ROLLBACK_SECONDS = 45;

/**
 * The address to open after the Pi left the Hotspot, which does not depend on the IP address it gets from the router.
 * @param {{port: string}} location e.g. `window.location`.
 * @return {string}
 */
export const addressOf = location => `http://mlsc.local${location.port ? `:${location.port}` : ''}`;

/**
 * What the status line says.
 * @param {{mode: string, connected: boolean, ssid: string|null, ip: string|null, hotspot: {ssid: string}|null}} status
 * @return {string}
 */
const summaryOf = (status) => {
    const ip = status.ip ? `, IP address ${status.ip}` : '';
    if (status.mode === 'hotspot' && status.hotspot) return `Hotspot ${status.hotspot.ssid} is on${ip}.`;
    if (status.connected && status.ssid) return `Connected to ${status.ssid}${ip}.`;
    return 'Not connected to a Wi-Fi network.';
};

/**
 * Which parts of the page to show for a status, and the banner for the diagnosis. The banner text comes from the server only.
 * @param {object} status The body of `GET /api/v2/wifi/status`.
 * @param {{pin_required: boolean}} session The body of `GET /api/v2/auth/session`.
 * @return {{unsupported: boolean, banner: {level: string, text: string, fix: string|null}|null, showStatus: boolean,
 *   showClient: boolean, showHotspot: boolean, showRadioButton: boolean, authWarning: boolean, summary: string,
 *   interface: string|null, hotspot: {ssid: string, password: string|null}|null}}
 */
export const pageView = (status, session) => {
    const usable = status.supported && status.radio === 'ready';
    const diagnosis = status.diagnosis;
    return {
        unsupported: !status.supported,
        banner: diagnosis.status === 'ok' ? null : { level: diagnosis.status, text: diagnosis.message, fix: diagnosis.suggested_fix },
        showStatus: status.supported,
        showClient: usable,
        showHotspot: usable && status.hotspot_supported,
        showRadioButton: status.supported && status.radio === 'switched_off',
        authWarning: !session.pin_required,
        summary: summaryOf(status),
        interface: status.interface,
        hotspot: status.hotspot,
    };
};

/**
 * Seconds of the Wi-Fi Rollback that are left.
 * @param {number} startedAt When the change was first seen pending, in ms.
 * @param {number} now In ms.
 * @return {number}
 */
export const secondsLeft = (startedAt, now) => Math.max(0, Math.ceil(ROLLBACK_SECONDS - (now - startedAt) / 1000));

const LEVELS = { confirmed: 'success', rolled_back: 'warning', failed: 'danger', pending: 'info' };

/**
 * The message for the state of a `wifi` Operation. Applying a change can drop the page's own connection, so every message
 * says where to find the Pi again.
 * @param {{state: string, error: string|null}} operation
 * @param {number} left Seconds of the Rollback that are left.
 * @param {string} address From `addressOf`.
 * @return {{level: string, text: string}}
 */
export const operationView = (operation, left, address) => {
    const where = `If this page stops answering, rejoin your home Wi-Fi and open ${address}.`;
    const error = operation.error ? ` ${operation.error}` : '';
    const texts = {
        pending: `Applying the Wi-Fi change… ${left} s left to connect, then MLSC goes back to the previous setting. ${where}`,
        confirmed: `The Wi-Fi change works. If you were using the Hotspot, rejoin your home Wi-Fi and open ${address}.`,
        rolled_back: `The Wi-Fi change was rolled back to the previous setting.${error}`,
        failed: `The Wi-Fi change failed.${error}`,
    };
    return { level: LEVELS[operation.state] || 'info', text: texts[operation.state] || texts.failed };
};

/**
 * How many of the four signal bars to light.
 * @param {number} signal 0 to 100.
 * @return {number} 0 to 4.
 */
export const signalLevel = signal => [20, 40, 55, 75].filter(limit => signal >= limit).length;

const SIGNAL_LABELS = ['Very weak', 'Weak', 'Good', 'Strong', 'Strong'];

/**
 * @param {number} signal 0 to 100.
 * @return {string}
 */
export const signalLabel = signal => SIGNAL_LABELS[signalLevel(signal)];

/**
 * What is wrong with the Hotspot name and password typed in, as the server would reject it. Empty means generated.
 * @param {string} ssid
 * @param {string} password
 * @return {string|null}
 */
export const hotspotProblem = (ssid, password) => {
    if (ssid.length > 32) return 'The Hotspot name can have at most 32 characters.';
    if (password && password.length < 8) return 'The Hotspot password needs at least 8 characters.';
    if (password.length > 63) return 'The Hotspot password can have at most 63 characters.';
    return null;
};

/**
 * What is wrong with the network name and password typed in, before the request is sent. A saved network needs no password.
 * @param {string} ssid
 * @param {string} password
 * @param {Array.<{ssid: string, security: string|null, known: boolean}>} networks The last scan.
 * @return {string|null}
 */
export const connectProblem = (ssid, password, networks) => {
    if (!ssid) return 'Enter or pick a network name first.';
    const network = networks.find(n => n.ssid === ssid);
    if (network && network.security && !network.known && !password) return `Enter the password for ${ssid}.`;
    if (password && (password.length < 8 || password.length > 63)) return 'A Wi-Fi password has 8 to 63 characters.';
    return null;
};
