import { api } from './classes/Api.js';
import { events } from './classes/Events.js';
import Toast from './classes/Toast.js';
import UnsavedChanges from './classes/UnsavedChanges.js';
import { addressOf, operationView, pageView, secondsLeft, signalLabel } from './classes/WifiView.js';

const unsaved = new UnsavedChanges(document.getElementById('settingsForm'));
const address = addressOf(window.location);

/** @type {object|null} The latest `GET /api/v2/wifi/status`. */
let status = null;
let session = { pin_required: true };
/** The `wifi` Operation being followed, and when it was first seen pending. */
let operation = null;
let operationStartedAt = 0;
let countdownTimer = null;

const LEVEL_CLASSES = 'alert-info alert-success alert-warning alert-danger';

const setAlert = ($alert, level, text) => $alert.removeClass(`d-none ${LEVEL_CLASSES}`).addClass(`alert-${level}`).text(text);

const render = () => {
    const view = pageView(status, session);
    $('#auth_warning').toggleClass('d-none', !view.authWarning);

    $('#banner').toggleClass('d-none', !view.banner);
    if (view.banner) {
        $('#banner').removeClass(LEVEL_CLASSES).addClass(`alert-${view.banner.level}`);
        $('#banner_text').text(view.banner.text);
        $('#banner_fix').text(view.banner.fix || '');
    }
    $('#radio_btn').toggleClass('d-none', !view.showRadioButton);

    $('#status_card').toggleClass('d-none', !view.showStatus);
    $('#summary').text(view.summary);
    $('#interface').text(view.interface || 'none');
    $('#address').text(address);
    $('#client_card').toggleClass('d-none', !view.showClient);
    $('#hotspot_card').toggleClass('d-none', !view.showHotspot);
    $('#saved_card').toggleClass('d-none', !view.showClient);

    const hotspotUp = Boolean(view.hotspot);
    $('#hotspot_info').toggleClass('d-none', !hotspotUp);
    $('#hotspot_off_btn').toggleClass('d-none', !hotspotUp);
    if (hotspotUp) {
        $('#hotspot_current_ssid').text(view.hotspot.ssid);
        // The API leaves the password out for an unauthenticated session while the PIN lock is on.
        $('#hotspot_current_password').text(view.hotspot.password || 'hidden');
    }
};

const loadStatus = async () => {
    [status, session] = await Promise.all([api.get('/wifi/status'), api.get('/auth/session')]);
    render();
};

/**
 * Show a list entry for a scanned network.
 * @param {{ssid: string, signal: number, security: string|null, in_use: boolean, known: boolean}} network
 * @return {jQuery}
 */
const networkItem = (network) => {
    const $item = $('<li class="list-group-item d-flex justify-content-between align-items-center"></li>');
    const $label = $('<span></span>').text(`${network.ssid} · ${signalLabel(network.signal)}${network.security ? ' · secured' : ' · open'}`);
    if (network.in_use) $label.append($('<span class="badge badge-success ml-2">connected</span>'));
    $item.append($label);
    return $item;
};

const showNetworks = (networks) => {
    const $networks = $('#networks').empty();
    const $saved = $('#saved').empty();
    networks.sort((a, b) => b.signal - a.signal).forEach((network) => {
        const $use = $('<button type="button" class="btn btn-sm btn-outline-primary">Use</button>').on('click', () => {
            $('#ssid').val(network.ssid);
            $('#password').val('').trigger('focus');
        });
        $networks.append(networkItem(network).append($use));
        if (network.known) {
            const $forget = $('<button type="button" class="btn btn-sm btn-outline-danger">Forget</button>').on('click', () => forget(network.ssid));
            $saved.append(networkItem(network).append($forget));
        }
    });
    $('#saved_empty').toggleClass('d-none', $saved.children().length > 0);
    $('#scan_info').text(networks.length ? '' : 'No networks found.');
};

const scan = async () => {
    const $button = $('#scan_btn').prop('disabled', true).text('Scanning…');
    try {
        showNetworks((await api.get('/wifi/scan')).networks);
    } catch (error) {
        new Toast(`Could not scan for networks. ${error.summary || ''}`).error();
    } finally {
        $button.prop('disabled', false).text('Scan for networks');
    }
};

const showOperation = () => {
    if (!operation) {
        $('#operation').addClass('d-none');
        return;
    }
    const view = operationView(operation, secondsLeft(operationStartedAt, Date.now()), address);
    setAlert($('#operation'), view.level, view.text);
};

/** Follow the `wifi` Operations the server publishes: the countdown of the Wi-Fi Rollback and its outcome. */
const onOperation = (event) => {
    if (event.kind !== 'wifi') return;
    if (!operation || operation.id !== event.id) operationStartedAt = Date.now();
    operation = event;
    clearInterval(countdownTimer);
    if (event.state === 'pending') countdownTimer = setInterval(showOperation, 1000);
    showOperation();
    if (event.state !== 'pending') loadStatus().then(scan).catch(() => {});
};

/** Run a change request, keeping its buttons off meanwhile. A refused change is a toast; its Operation shows the outcome. */
const change = async (buttons, request, failure) => {
    const $buttons = $(buttons).prop('disabled', true);
    try {
        await request();
        unsaved.markClean();
    } catch (error) {
        new Toast(`${failure} ${error.summary || ''}`).error();
    } finally {
        $buttons.prop('disabled', false);
    }
};

const connect = () => {
    const ssid = $('#ssid').val().trim();
    if (!ssid) {
        new Toast('Enter or pick a network name first.').info();
        return Promise.resolve();
    }
    const password = $('#password').val();
    return change('#connect_btn', async () => {
        status = await api.post('/wifi/connect', { ssid, password: password || null });
        $('#password').val('');
        render();
    }, 'Could not join the network.');
};

const forget = (ssid) => {
    if (!window.confirm(`Forget the network ${ssid}?`)) return Promise.resolve();
    return change('#saved button', async () => {
        await api.post('/wifi/forget', { ssid });
        new Toast(`Forgot ${ssid}.`).success();
        await scan();
    }, 'Could not forget the network.');
};

const setHotspot = (enabled) => {
    const body = { enabled };
    if (enabled) {
        const ssid = $('#hotspot_ssid').val().trim();
        const password = $('#hotspot_password').val();
        if (ssid) body.ssid = ssid;
        if (password) body.password = password;
    }
    return change('#hotspot_on_btn, #hotspot_off_btn', async () => {
        status = await api.put('/wifi/hotspot', body);
        $('#hotspot_password').val('');
        render();
    }, `Could not switch the Hotspot ${enabled ? 'on' : 'off'}.`);
};

const enableRadio = () => change('#radio_btn', async () => {
    status = await api.put('/wifi/radio', { enabled: true });
    render();
    if (status.radio === 'ready') scan();
}, 'Could not turn Wi-Fi on.');

$(() => {
    loadStatus().then(() => {
        unsaved.markClean();
        if (pageView(status, session).showClient) scan();
    }).catch(error => new Toast(`Error while loading the Wi-Fi status. ${error.summary || ''}`).error());

    events.on('wifi.state', () => loadStatus().catch(() => {}));
    events.on('operation', onOperation);

    $('#scan_btn').on('click', scan);
    $('#connect_btn').on('click', connect);
    $('#hotspot_on_btn').on('click', () => setHotspot(true));
    $('#hotspot_off_btn').on('click', () => setHotspot(false));
    $('#radio_btn').on('click', enableRadio);
});
