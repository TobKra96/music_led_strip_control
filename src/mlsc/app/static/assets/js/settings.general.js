import { api } from './classes/Api.js';
import Toast from './classes/Toast.js';
import UnsavedChanges from './classes/UnsavedChanges.js';
import Tagin from '../plugins/tagin/js/tagin.js';

/** @type {Tagin} */
let tagin;

/** Settings that are still edited through the v1 API, until the microphone has its own v2 resource. */
const MICROPHONE_KEYS = ['device_id', 'default_sample_rate', 'min_frequency', 'max_frequency', 'min_volume_threshold', 'frames_per_buffer'];

const pick = (obj, keys) => Object.fromEntries(Object.entries(obj).filter(([key]) => keys.includes(key)));
const omit = (obj, keys) => Object.fromEntries(Object.entries(obj).filter(([key]) => !keys.includes(key)));

// Init and load all settings.
$(() => {
    // Allow to scroll sidebar when page is reloaded and mouse is already on top of sidebar.
    $('.navbar-content').trigger('mouseover');

    $('#settings_list').slideDown();

    const taginOptions = {
        separator: ',',
        duplicate: false,
        enter: true,
        transform: input => input,
        placeholder: 'Add a group...',
        maximum: 100
    };
    tagin = new Tagin(document.querySelector('.tagin'), taginOptions);

    const unsaved = new UnsavedChanges(document.getElementById('settingsForm'));

    /** The PIN stored on the server. The v2 API cannot save the lock without a PIN, so this stands in for an emptied field. */
    let savedPin = '';

    // Preload dropdown values.
    const promises = [

        api.get('/resources/logging-levels').then((data) => {
            $.each(data, (key, value) => {
                $('.logging_levels').append(`<option value='${key}'>${value}</option>`);
            });
        }),

        api.get('/resources/audio-devices').then((data) => {
            $.each(data, (key, value) => {
                $('.audio_devices').append(`<option value='${key}'>${value}</option>`);
            });
        })

    ]

    /**
     * Populate general settings with config values.
     * @param {object} settings
     */
    const populateGeneralSettings = (settings) => {
        if ('device_groups' in settings) tagin.clearTags();
        $.each(settings, (key, value) => {
            const el = $(`#${key}`);
            if (el.is(':checkbox')) {
                el.prop('checked', value);
            } else if (el.is('select')) {
                el.val(value);
            } else if (el.hasClass('tagin')) {
                tagin.addTag(value);
            } else {
                el.val(value);
            }
            el.trigger('change');
        });
    }

    /**
     * Populate PIN settings with `security.ini` values.
     * @param {PinSettings} settings
     */
    const populatePinSettings = (settings) => {
        savedPin = settings.default_pin;
        $('#DASHBOARD_PIN').val(settings.default_pin);
        $('#PIN_LOCK_ENABLED').prop('checked', settings.use_pin_lock);
    }

    /**
     * Call API to get all general settings.
     * The microphone settings have no v2 resource yet, so they are still read and written through the v1 API.
     */
    const getLocalSettings = () => {
        const settingsPromises = [

            api.get('/settings').then((data) => {
                populateGeneralSettings(omit(data, MICROPHONE_KEYS));
            }),

            api.get('/groups').then((groups) => {
                populateGeneralSettings({ device_groups: Object.fromEntries(groups.map(g => [g.id, g.name])) });
            }),

            $.ajax('/api/settings/general').done((data) => {
                populateGeneralSettings(pick(data.setting_value, MICROPHONE_KEYS));
            }),

            api.get('/auth/pin').then((data) => {
                populatePinSettings(data);
            })

        ]

        // The form counts as saved once it is populated. Reset and import come through here as well.
        Promise.all(settingsPromises).then(() => {
            unsaved.markClean();
        }).catch((error) => {
            new Toast(`Error while getting general settings. ${error.summary || ''}`).error();
        });
    }

    /**
     * Check if PIN is valid before serializing general settings.
     * @return {boolean}
     */
    const _isPinValid = () => {
        const isPinActive = $('#PIN_LOCK_ENABLED').prop('checked');
        const pinLen = $('#DASHBOARD_PIN').val().length;
        return (isPinActive && pinLen >= 4) || (!isPinActive && (pinLen === 0 || pinLen >= 4));
    }

    /**
     * Call API to set general settings.
     * @param {object} settings
     * @return {Promise}
     */
    const setGeneralSettings = (settings) => {
        const microphone = pick(settings, MICROPHONE_KEYS);
        const general = omit(settings, [...MICROPHONE_KEYS, 'device_groups']);

        return Promise.all([
            api.patch('/settings', general),
            $.ajax({
                url: '/api/settings/general',
                type: 'POST',
                data: JSON.stringify({ settings: microphone }),
                contentType: 'application/json;charset=UTF-8'
            }),
            setGroups(settings.device_groups),
        ]);
    }

    /**
     * Create the groups that were added as tags and delete the ones that were removed.
     * @param {Object.<string, string>} wanted Group names by tag id.
     */
    const setGroups = async (wanted) => {
        if (!wanted) return;  // The form did not send any groups.
        const current = await api.get('/groups');
        const wantedNames = Object.values(wanted);
        const currentNames = current.map(g => g.name);

        await Promise.all(current.filter(g => !wantedNames.includes(g.name)).map(g => api.delete(`/groups/${g.id}`)));
        // Created one after another, as each one is given the next free id.
        for (const name of wantedNames.filter(n => !currentNames.includes(n))) {
            await api.post('/groups', { name });
        }
    }

    /**
     * Call API to set validated PIN settings.
     * @param {object} settings
     * @return {Promise}
     */
    const setPinSettings = (settings) => {
        // The API only accepts 4 to 8 digits. An empty PIN is only allowed while the lock is off: keep the saved PIN then.
        const pin = settings.DASHBOARD_PIN || savedPin;
        if (!pin) return Promise.resolve();

        return api.put('/auth/pin', {
            default_pin: pin,
            use_pin_lock: settings.PIN_LOCK_ENABLED
        }).then((saved) => {
            savedPin = saved.default_pin;
        });
    }

    /**
     * Serialize general settings as JSON.
     */
    const setLocalSettings = () => {

        if (!_isPinValid()) {
            new Toast('PIN should be more than 4 digits long.').error();
            return;
        }

        const serializedForm = $('#settingsForm .setting_input').serializeJSON({
            checkboxUncheckedValue: 'false',
            customTypes: {
                port: (value) => {
                    return !value || value === '0' || isNaN(value) ? 8080 : parseInt(value);
                },
                tags: () => { return tagin.getTagObjects(); }
            }
        });

        const serializedPinForm = $('#settingsForm .pin_setting').serializeJSON({
            checkboxUncheckedValue: 'false',
            customTypes: {
                pin: (value) => {
                    return value.length < 4 || isNaN(value) ? '' : value;
                }
            }
        });

        Promise.all([setGeneralSettings(serializedForm), setPinSettings(serializedPinForm)]).then(() => {
            unsaved.markClean();
            new Toast('General settings saved.').success();
        }).catch((error) => {
            new Toast(`Error while saving general settings. ${error.summary || ''}`).error();
        });
    }

    /**
     * Call API to reset the whole configuration, devices and groups included, to default values.
     */
    const resetSettings = () => {
        Promise.all([api.post('/config/reset'), api.delete('/auth/pin')]).then(() => {
            getLocalSettings();
            new Toast('Configuration reset to default.').success();
        }).catch((error) => {
            new Toast(`Error while resetting settings. ${error.summary}`).error();
        });
    }

    /**
     * Call API to import new config file.
     */
    const importSettings = async () => {
        const file = $('#configUpload').prop('files')[0];

        if (!file) {
            new Toast('No config file selected.').error();
            return;
        }

        try {
            await api.put('/config', JSON.parse(await file.text()));
        } catch (error) {
            const reason = error instanceof SyntaxError ? 'The file is not valid JSON.' : error.summary;
            new Toast(`Error while importing general settings. ${reason}`).error();
            return;
        }
        getLocalSettings();
        new Toast('General settings imported.').success();
    }

    Promise.all(promises).then(() => {
        getLocalSettings();
    }).catch((error) => {
        new Toast(`Error while preloading dropdown values. ${error.summary}`).error();
    });

    $('#save_btn').on('click', () => {
        setLocalSettings();
    });

    $('#reset_btn').on('click', () => {
        $('#modal_reset_general').modal('show');
    });

    $('#reset_btn_modal').on('click', () => {
        $('#modal_reset_general').modal('hide');
        resetSettings();
    });

    $('#export_btn').on('click', () => {
        new Toast('Configuration file exported.').success();
    });

    $('#import_btn').on('click', () => {
        importSettings();
    });

    // Insert filename of imported config.
    $('.custom-file-input').on('change', e => {
        const fileName = $('#configUpload').val().split('\\').pop();
        let nextSibling = e.target.nextElementSibling;
        nextSibling.innerText = fileName;
    })

    // Toggle PIN visibility on hover.
    $('#toggle_pin_view').on('mouseover mouseleave', () => {
        const pinField = $('#DASHBOARD_PIN');
        pinField.prop('type') === 'text' ? pinField.prop('type', 'password') : pinField.prop('type', 'text');
        $('#toggle_pin_view').toggleClass('icon-eye');
        $('#toggle_pin_view').toggleClass('icon-eye-off');
    });

});


// Tooltip descriptions for general settings.
$('#WEBSERVER_PORT_TOOLTIP').attr('data-original-title', 'The port used by the web server.<br>Changing this, the web interface will be available on another port. Example:<br>http://[raspberry_pi_ip]:8080<br><br>Default setting: 8080');
$('#DASHBOARD_PIN_TOOLTIP').attr('data-original-title', 'The PIN code for locking the web interface from unwanted access.<br>Only 4 to 8 digits are allowed.<br>Enable or disable the PIN Lock feature using the checkbox below.');
$('#DEVICE_ID_TOOLTIP').attr('data-original-title', 'The device ID of your microphone.<br>This audio device will be used for the music reactive effects.');
$('#DEFAULT_SAMPLE_RATE_TOOLTIP').attr('data-original-title', 'The sample rate of your microphone.<br>You can find it inside the console output.<br><br>Common values are 44100 or 48000.');
$('#MIN_FREQUENCY_TOOLTIP').attr('data-original-title', 'The minimum frequency supported by your microphone.<br>This will increase the quality of your effects.<br><br>Default setting: 50');
$('#MAX_FREQUENCY_TOOLTIP').attr('data-original-title', 'The maximum frequency supported by your microphone.<br>This will increase the quality of your effects.<br><br>Default setting: 16000');
$('#MIN_VOLUME_THRESHOLD_TOOLTIP').attr('data-original-title', 'The minimum volume level of your microphone that has to be reached before the program will recognize the audio signal.<br>It filters background noises and reduces the rate of false triggers.<br><br>Default setting: 0.001');
$('#N_ROLLING_HISTORY_TOOLTIP').attr('data-original-title', 'The amount of audio snapshots that will be stored for the calculation of the rhythm.<br><br>Default setting: 4');
$('#FRAMES_PER_BUFFER_TOOLTIP').attr('data-original-title', 'The buffer size of the audio signal.<br>More buffer frames cause lower frame rates, but higher effect quality.<br>Less buffer frames cause high frame rates, but lower effect quality.<br><br>Default setting: 512');
$('#N_FFT_BINS_TOOLTIP').attr('data-original-title', 'The amount of slices that the audio spectrum will be divided into.<br><br>Default setting: 24');
$('#LOG_LEVEL_CONSOLE_TOOLTIP').attr('data-original-title', 'The logging verbosity level in the console.<br><br>Default setting: info');
$('#LOG_LEVEL_FILE_TOOLTIP').attr('data-original-title', 'The logging verbosity level in a log file.<br>Enable or disable file logging using the checkbox below.<br><br>Use this only for debugging.<br>File logging for extensive periods of time could cause SD card wear-out.<br><br>Default setting: info');
$('#MODIFY_GLOBAL_GROUP_TOOLTIP').attr('data-original-title', 'Add or remove group tags, which can be used to organize devices. Maximum 100 groups allowed.');

/**
 * @typedef {import('jquery')} $ - Type definition for jQuery.
 */

/**
 * @typedef {object} PinSettings
 * @property {string} default_pin
 * @property {boolean} use_pin_lock
 */
