import { api } from './classes/Api.js';
import { events } from './classes/Events.js';
import Toast from './classes/Toast.js';
import UnsavedChanges from './classes/UnsavedChanges.js';
import { addressOf, operationView, pageView, secondsLeft, signalLabel, signalLevel } from './classes/WifiView.js';

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
    $('#hotspot_state').text(hotspotUp ? 'On' : 'Off').toggleClass('badge_green', hotspotUp).toggleClass('badge-secondary', !hotspotUp);
    $('#hotspot_on_btn').toggleClass('d-none', hotspotUp);
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
 * The four signal bars, lit up to the level of the signal.
 * @param {number} signal 0 to 100.
 * @return {jQuery}
 */
const signalBars = (signal) => {
    const level = signalLevel(signal);
    const text = `Signal: ${signalLabel(signal)}`;
    const $bars = $('<span class="wifi-signal" role="img"></span>')
        .attr('aria-label', text).attr('title', `${text} (${signal}%)`)
        .toggleClass('weak', level <= 1);
    for (let bar = 1; bar <= 4; bar += 1) $bars.append($('<span></span>').toggleClass('on', bar <= level));
    return $bars;
};

/**
 * Show a list entry for a scanned network: signal bars, the name, a lock for a secured network and the action.
 * @param {{ssid: string, signal: number, security: string|null, in_use: boolean, known: boolean}} network
 * @param {jQuery} $action
 * @return {jQuery}
 */
const networkItem = (network, $action) => {
    const secured = Boolean(network.security);
    const $lock = $(`<span class="wifi-lock feather ${secured ? 'icon-lock' : 'icon-unlock'}" role="img"></span>`)
        .attr('aria-label', secured ? 'Secured' : 'Open network')
        .attr('title', secured ? `Secured (${network.security})` : 'Open network, no password');
    const $name = $('<span class="wifi-network-name"></span>').text(network.ssid);
    $name.append($('<span class="wifi-network-meta"></span>').text([signalLabel(network.signal), secured ? 'secured' : 'open'].join(' · ')));
    const $item = $('<li class="wifi-network"></li>').attr('data-ssid', network.ssid).append(signalBars(network.signal), $name, $lock);
    if (network.in_use) $item.append($('<span class="badge badge_green">connected</span>'));
    return $item.append($action);
};

/** Mark the listed network whose name is typed in the form. */
const markSelected = () => $('#networks .wifi-network').each(function () {
    $(this).toggleClass('selected', $(this).attr('data-ssid') === $('#ssid').val());
});

const showNetworks = (networks) => {
    const $networks = $('#networks').empty();
    const $saved = $('#saved').empty();
    networks.sort((a, b) => b.signal - a.signal).forEach((network) => {
        const $use = $('<button type="button" class="btn btn-primary btn-sm">Use</button>').on('click', () => {
            $('#ssid').val(network.ssid);
            $('#password').val('').trigger('focus');
            markSelected();
        });
        $networks.append(networkItem(network, $use));
        if (network.known) {
            const $forget = $('<button type="button" class="btn btn-outline-danger btn-sm"><span class="feather icon-trash-2"></span> Forget</button>')
                .on('click', () => forget(network.ssid));
            $saved.append(networkItem(network, $forget));
        }
    });
    if (!networks.length) $networks.append('<li class="wifi-empty text-muted">No networks found. Move the Pi closer to a router, then scan again.</li>');
    $('#saved_empty').toggleClass('d-none', $saved.children().length > 0);
    $('#scan_info').text(networks.length ? `${networks.length} network${networks.length === 1 ? '' : 's'} found` : '');
    markSelected();
};

const scan = async () => {
    const $button = $('#scan_btn').prop('disabled', true).html('<span class="feather icon-refresh-cw"></span> Scanning…');
    try {
        showNetworks((await api.get('/wifi/scan')).networks);
    } catch (error) {
        new Toast(`Could not scan for networks. ${error.summary || ''}`).error();
    } finally {
        $button.prop('disabled', false).html('<span class="feather icon-refresh-cw"></span> Scan for networks');
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
    const $button = $(enabled ? '#hotspot_on_btn' : '#hotspot_off_btn');
    const label = $button.text();
    $button.text(enabled ? 'Switching on…' : 'Switching off…');
    return change('#hotspot_on_btn, #hotspot_off_btn', async () => {
        status = await api.put('/wifi/hotspot', body);
        $('#hotspot_password').val('');
        render();
        new Toast(`The Hotspot is ${status.hotspot ? 'on' : 'off'}.`).success();
    }, `Could not switch the Hotspot ${enabled ? 'on' : 'off'}.`).finally(() => $button.text(label));
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
    $('#ssid').on('input', markSelected);
    $('#hotspot_on_btn').on('click', () => setHotspot(true));
    $('#hotspot_off_btn').on('click', () => setHotspot(false));
    $('#radio_btn').on('click', enableRadio);
});
