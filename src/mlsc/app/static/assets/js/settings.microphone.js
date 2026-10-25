import { api } from './classes/Api.js';
import { events } from './classes/Events.js';
import Toast from './classes/Toast.js';
import UnsavedChanges from './classes/UnsavedChanges.js';
import { BrowserMicrophone } from './classes/BrowserMicrophone.js';

const unsaved = new UnsavedChanges(document.getElementById('settingsForm'));

/** Device options, by the value of their `<option>`. The empty value is the system default. */
let deviceChoices = new Map();
/** @type {Array.<{name: string, host_api: string, default_sample_rate: number, sample_rates: Array.<number>, monitor: boolean, default: boolean}>} */
let devices = [];
/** The settings as last loaded or saved. */
let settings = {};

const NUMBER_FIELDS = ['min_frequency', 'max_frequency', 'min_volume_threshold'];
const TEST_LEVELS = { ok: 'alert-success', silence: 'alert-warning' };

const deviceKey = (name, hostApi) => (name === null ? '' : JSON.stringify([name, hostApi]));

/**
 * @param {{name: string, host_api: string, default_sample_rate: number, monitor: boolean, default: boolean}} device
 * @return {string}
 */
const deviceLabel = device => [
    device.name,
    device.host_api ? `(${device.host_api})` : '',
    `${device.default_sample_rate} Hz`,
    device.monitor ? '· Monitor' : '',
    device.default ? '· default' : '',
].filter(Boolean).join(' ');

/** The device the selection stands for, or the system default for the empty value. */
const selectedDevice = () => {
    const value = $('#device').val();
    return value ? deviceChoices.get(value) : devices.find(d => d.default);
};

const fillDevices = () => {
    deviceChoices = new Map();
    const $select = $('#device').empty().append('<option value="">System default</option>');
    devices.forEach((device) => {
        const key = deviceKey(device.name, device.host_api);
        deviceChoices.set(key, device);
        $select.append($('<option></option>').val(key).text(deviceLabel(device)));
    });

    // Keep a stored device that is not plugged in selectable, so saving other changes does not drop it.
    if (settings.device_name !== null && !devices.some(d => d.name === settings.device_name && [null, d.host_api].includes(settings.host_api))) {
        const key = deviceKey(settings.device_name, settings.host_api);
        deviceChoices.set(key, { name: settings.device_name, host_api: settings.host_api, sample_rates: [], missing: true });
        $select.append($('<option></option>').val(key).text(`${settings.device_name} (not found)`));
    }
};

/** Offer the native rate plus the rates the selected device supports. */
const fillSampleRates = (selected) => {
    const device = selectedDevice();
    const $select = $('#sample_rate').empty();
    $select.append($('<option value="">Native</option>').text(device && device.default_sample_rate ? `Native (${device.default_sample_rate} Hz)` : 'Native'));
    const rates = new Set(device ? device.sample_rates : []);
    if (selected) rates.add(selected);
    [...rates].sort((a, b) => a - b).forEach(rate => $select.append($('<option></option>').val(rate).text(`${rate} Hz`)));
    $select.val(selected ? String(selected) : '');
};

const showDeviceInfo = () => {
    const device = selectedDevice();
    const info = settings.source === 'browser' ? 'The Browser Microphone is selected. Save a device here to switch back to a microphone on the server.'
        : device && device.missing ? 'This device is not connected. MLSC uses the system default until it is back.'
        : device && device.monitor ? 'Monitor Device: carries audio played on this computer or received from a remote source.'
            : '';
    $('#device_info').text(info);
};

const populate = (values) => {
    settings = values;
    fillDevices();
    $('#device').val(deviceKey(settings.device_name, settings.host_api));
    fillSampleRates(settings.sample_rate);
    $('#frames_per_buffer').val(String(settings.frames_per_buffer));
    $('#gain').val(settings.gain);
    $("span[for='gain']").text(`${Number(settings.gain).toFixed(1)}×`);
    NUMBER_FIELDS.forEach(key => $(`#${key}`).val(settings[key]));
    showDeviceInfo();
    unsaved.markClean();
};

/** Only the values that differ from the loaded settings. */
const collectChanges = () => {
    const device = $('#device').val() ? deviceChoices.get($('#device').val()) : null;
    const form = {
        source: 'device',
        device_name: device ? device.name : null,
        host_api: device ? device.host_api : null,
        gain: Number($('#gain').val()),
        sample_rate: $('#sample_rate').val() ? Number($('#sample_rate').val()) : null,
        frames_per_buffer: Number($('#frames_per_buffer').val()),
    };
    NUMBER_FIELDS.forEach((key) => { form[key] = Number($(`#${key}`).val()); });
    return Object.fromEntries(Object.entries(form).filter(([key, value]) => value !== settings[key]));
};

/**
 * Resolve with the final state of an Operation, from its `operation` events or, as a fallback, by polling.
 * @param {{id: string, state: string}} operation
 * @return {Promise.<{state: string, error: string|null}>}
 */
const waitForOperation = operation => new Promise((resolve) => {
    let done = false;
    const finish = (result) => {
        if (done || result.id !== operation.id || result.state === 'pending') return;
        done = true;
        clearInterval(timer);
        resolve(result);
    };
    events.on('operation', finish);
    const timer = setInterval(() => api.get(`/operations/${operation.id}`).then(finish).catch(() => {}), 1000);
    finish(operation);
});

const save = async () => {
    const changes = collectChanges();
    if (!Object.keys(changes).length) {
        new Toast('Nothing to save.').info();
        return;
    }
    const $button = $('#save_btn').prop('disabled', true).text('Saving…');
    try {
        const operation = await waitForOperation(await api.patch('/microphone', changes));
        if (operation.state === 'confirmed') {
            new Toast('Microphone settings saved.').success();
        } else {
            new Toast(`The new settings did not work and were rolled back. ${operation.error || ''}`).error();
        }
        await load();
    } catch (error) {
        new Toast(`Could not save the microphone settings. ${error.summary || ''}`).error();
    } finally {
        $button.prop('disabled', false).text('Save');
    }
};

const BROWSER_STATES = {
    starting: ['alert-info', 'Starting…'],
    streaming: ['alert-success', 'Streaming from this browser. Keep this page open.'],
    insecure: ['alert-warning', 'The browser only allows microphone access on HTTPS or localhost. See the details link for how to enable HTTPS.'],
    denied: ['alert-danger', 'Microphone access was denied. Allow it for this site in the browser, then try again.'],
    no_device: ['alert-danger', 'This device has no microphone.'],
    stopped: ['alert-warning', ''],
    error: ['alert-danger', ''],
};

const showBrowserState = (state, detail) => {
    const [level, text] = BROWSER_STATES[state] || [];
    const streaming = state === 'streaming';
    $('#browser_btn').prop('disabled', state === 'starting').text(streaming ? 'Stop streaming' : 'Stream from this browser');
    $('#browser_status').toggleClass('d-none', !text && !detail)
        .removeClass('alert-info alert-success alert-warning alert-danger').addClass(level || '')
        .text([text, detail].filter(Boolean).join(' '));
};

const browserMicrophone = new BrowserMicrophone({
    isSecureContext: window.isSecureContext,
    mediaDevices: navigator.mediaDevices,
    createContext: () => new AudioContext(),
    createWorkletNode: context => new AudioWorkletNode(context, 'mono-int16', { numberOfInputs: 1, numberOfOutputs: 1, channelCount: 1 }),
    workletUrl: '/static/assets/js/browser-microphone.worklet.js',
    wakeLock: navigator.wakeLock,
    openStream: () => api.post('/microphone/browser/stream'),
    fetch: (url, options) => fetch(url, options),
    onState: showBrowserState,
});

/** Select the Browser Microphone if it is not yet, so the server accepts the stream. */
const toggleBrowserStream = async () => {
    if (browserMicrophone.state === 'streaming') {
        await browserMicrophone.stop();
        return;
    }
    try {
        if (settings.source !== 'browser') {
            const operation = await waitForOperation(await api.patch('/microphone', { source: 'browser' }));
            if (operation.state !== 'confirmed') throw new Error(operation.error || 'The Browser Microphone could not be selected.');
            await load();
        }
    } catch (error) {
        new Toast(`Could not select the Browser Microphone. ${error.summary || error.message}`).error();
        return;
    }
    await browserMicrophone.start();
};

const showMixer = (mixer) => {
    $('#hardware_gain_group').toggleClass('d-none', !mixer.available);
    if (!mixer.available) return;
    $('#hardware_gain').val(mixer.level);
    $("span[for='hardware_gain']").text(`${mixer.level}%`);
    $('#hardware_gain_info').text(`Mixer control "${mixer.control}" on card ${mixer.card}. Takes effect at once.`);
};

const loadMixer = () => api.get('/microphone/mixer').then(showMixer).catch(() => showMixer({ available: false }));

const load = async () => {
    const [values, deviceList] = await Promise.all([api.get('/microphone'), api.get('/microphone/devices')]);
    // The Browser Microphone entry is picked by the browser streaming client, not through the device list.
    devices = deviceList.devices.filter(d => d.source !== 'browser');
    const $frames = $('#frames_per_buffer').empty();
    const choices = new Set([...deviceList.frames_per_buffer, values.frames_per_buffer]);
    [...choices].sort((a, b) => a - b).forEach(frames => $frames.append($('<option></option>').val(frames).text(frames)));
    populate(values);
    loadMixer();
};

const showStatus = (status) => {
    let text = '';
    if (status.state === 'ok') text = `Listening to ${status.device} at ${status.sample_rate} Hz.`;
    else if (status.state === 'starting') text = `Opening ${status.device}…`;
    else if (status.state === 'error') text = 'No audio. See the message at the top of the page.';
    else if (status.state === 'waiting') text = 'Waiting for browser';
    if (status.unstable) text += ' Unstable connection: audio from the browser keeps dropping out.';
    $('#status_text').text(text.trim());
};

const test = async () => {
    const $button = $('#test_btn').prop('disabled', true).text('Listening…');
    const $result = $('#test_result').addClass('d-none');
    try {
        const result = await api.post('/microphone/test');
        $result.removeClass('d-none alert-success alert-warning alert-danger')
            .addClass(TEST_LEVELS[result.result] || 'alert-danger')
            .empty()
            .append($('<strong class="d-block"></strong>').text(result.message));
        if (result.hint) $result.append($('<span></span>').text(result.hint));
        showRecording(result);
    } catch (error) {
        new Toast(`Could not test the microphone. ${error.summary || ''}`).error();
    } finally {
        $button.prop('disabled', false).text('Test microphone');
    }
};

$(() => {
    load().catch(error => new Toast(`Error while loading the microphone settings. ${error.summary || ''}`).error());
    api.get('/microphone/status').then(showStatus).catch(() => {});

    events.on('mic.level', ({ level }) => {
        const percent = Math.round(level * 100);
        $('#level_meter').css('width', `${percent}%`)
            .toggleClass('bg-success', level < 0.9).toggleClass('bg-danger', level >= 0.9);
        $('.progress[role=progressbar]').attr('aria-valuenow', percent);
    });
    events.on('audio.status', (status) => {
        showStatus(status);
        loadMixer();
    });

    $('#device').on('change', () => {
        fillSampleRates(null);
        showDeviceInfo();
    });
    $('#gain').on('input', function () {
        $("span[for='gain']").text(`${Number(this.value).toFixed(1)}×`);
    });
    $('#hardware_gain').on('input', function () {
        $("span[for='hardware_gain']").text(`${this.value}%`);
    }).on('change', function () {
        api.put('/microphone/mixer', { level: Number(this.value) })
            .then(showMixer)
            .catch(error => new Toast(`Could not set the hardware gain. ${error.summary || ''}`).error());
    });
    $('#save_btn').on('click', save);
    $('#test_btn').on('click', test);
    $('#browser_btn').on('click', toggleBrowserStream);
    // Give the claim back instead of leaving the server to time out. `keepalive` lets the request outlive the page.
    window.addEventListener('pagehide', () => { browserMicrophone.stop(); });
});
