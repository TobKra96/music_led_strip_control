import Toast from './classes/Toast.js';
import Tagin from '../plugins/tagin/js/tagin.js';

/** @type {Tagin} */
let tagin;

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

    // Preload dropdown values.
    const promises = [

        $.ajax('/api/resources/logging-levels').done((data) => {
            $.each(data, (key, value) => {
                $('.logging_levels').append(`<option value='${key}'>${value}</option>`);
            });
        }),

        $.ajax('/api/resources/audio-devices').done((data) => {
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
        tagin.clearTags();
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
        $('#DASHBOARD_PIN').val(settings.DEFAULT_PIN);
        $('#PIN_LOCK_ENABLED').prop('checked', settings.USE_PIN_LOCK);
    }

    /**
     * Call API to get all general settings.
     */
    const getLocalSettings = () => {
        const settingsPromises = [

            $.ajax('/api/settings/general').done((data) => {
                populateGeneralSettings(data.setting_value);
            }),

            $.ajax('/api/auth/pin').done((data) => {
                populatePinSettings(data);
            })

        ]

        Promise.all(settingsPromises).catch((data) => {
            console.log(`Error while getting general settings. Error:\n\n${data.responseText}`);
            new Toast('Error while getting general settings.').error();
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
     */
    const setGeneralSettings = (settings) => {
        const generalSettings = { settings };

        $.ajax({
            url: '/api/settings/general',
            type: 'POST',
            data: JSON.stringify(generalSettings),
            contentType: 'application/json;charset=UTF-8'
        }).done((data) => {
            console.log(`General settings set successfully. Response:\n\n${JSON.stringify(data, null, '\t')}`);
            new Toast('General settings saved.').success();

            $.ajax({
                url: '/api/system/groups',
                type: 'PATCH',
                contentType: 'application/json;charset=UTF-8'
            }).done((data) => {
                console.log(`Removing any stray device groups:\n\n${JSON.stringify(data, null, '\t')}`);
            });

        }).fail((data) => {
            console.log(`Error while setting general settings. Error:\n\n${data.responseText}`);
            new Toast('Error while saving general settings.').error();
        });
    }

    /**
     * Call API to set validated PIN settings.
     * @param {object} settings
     */
    const setPinSettings = (settings) => {
        const pinData = {
            DEFAULT_PIN: settings.DASHBOARD_PIN,
            USE_PIN_LOCK: settings.PIN_LOCK_ENABLED
        };

        $.ajax({
            url: '/api/auth/pin',
            type: 'POST',
            data: JSON.stringify(pinData),
            contentType: 'application/json;charset=UTF-8'
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

        setGeneralSettings(serializedForm);
        setPinSettings(serializedPinForm);
    }

    /**
     * Call API to reset PIN settings to default values.
     */
    const resetPinSettings = () => {
        $.ajax({
            url: '/api/auth/pin',
            type: 'DELETE',
            contentType: 'application/json;charset=UTF-8'
        });
    }

    /**
     * Call API to reset general settings to default values.
     */
    const resetSettings = () => {
        $.ajax({
            url: '/api/settings/general',
            type: 'DELETE',
            contentType: 'application/json;charset=UTF-8'
        }).done(() => {
            getLocalSettings();
            console.log('Settings reset successfully.');
            new Toast('General settings reset to default.').success();
        }).fail((data) => {
            console.log(`Error while resetting settings. Error:\n\n${data.responseText}`);
            new Toast('Error while resetting settings.').error();
        });
    }

    /**
     * Call API to import new config file.
     */
    const importSettings = () => {
        const fileData = $('#configUpload').prop('files')[0];

        if (!fileData) {
            new Toast('No config file selected.').error();
            return;
        }

        const formData = new FormData();
        formData.append('imported_config', fileData);

        $.ajax({
            url: '/api/settings/configuration/file',
            dataType: 'text',
            cache: false,
            contentType: false,
            processData: false,
            data: formData,
            type: 'POST'
        }).done(() => {
            getLocalSettings();
            console.log('General settings imported.');
            new Toast('General settings imported.').success();
        }).fail((data) => {
            console.log(`Error while importing general settings. Error:\n\n${data.responseText}`);
            new Toast('Error while importing general settings.').error();
        });
    }

    Promise.all(promises).then(() => {
        getLocalSettings();
    }).catch((data) => {
        console.log(data);
        new Toast('Error while preloading dropdown values.').error();
    });

    $('#save_btn').on('click', () => {
        setLocalSettings();
    });

    $('#reset_btn').on('click', () => {
        $('#modal_reset_general').modal('show');
    });

    $('#reset_btn_modal').on('click', () => {
        $('#modal_reset_general').modal('hide');
        resetPinSettings();
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
 * @property {string} DEFAULT_PIN
 * @property {string} USE_PIN_LOCK
 */
