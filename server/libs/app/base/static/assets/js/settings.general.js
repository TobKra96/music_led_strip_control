import Toast from "./classes/Toast.js";
import Tagin from "../plugins/tagin/js/tagin.js";

let tagin;

// Init and load all settings
$(document).ready(() => {
    $("#settings_list").slideDown();
    $("#device_dropdown").hide();

    const taginOptions = {
        separator: ',',
        duplicate: false,
        enter: true,
        transform: input => input,
        placeholder: 'Add a group...'
    };
    tagin = new Tagin(document.querySelector(".tagin"), taginOptions);

    // Preload dropdown values.
    Promise.all([

        $.ajax("/api/resources/logging-levels").done((response) => {
            $('.logging_levels').each(function () {
                Object.entries(response).forEach(([key, value]) => {
                    $(this).append(`<option value="${key}">${value}</option>`);
                });
            });
        }),

        $.ajax("/api/resources/audio-devices").done((response) => {
            $('.audio_devices').each(function () {
                Object.entries(response).forEach(([key, value]) => {
                    $(this).append(`<option value="${key}">${value}</option>`);
                });
            });
        })

    ]).then(() => {
        getLocalSettings();
    }).catch((response) => {
        new Toast(JSON.stringify(response, null, '\t')).error();
    });

});

/**
 * Call API to get all general settings.
 */
function getLocalSettings() {
    Promise.all([

        $.ajax("/api/settings/general").done((response) => {
            populateGeneralSettings(response.setting_value);
        }),

        $.ajax("/api/auth/pin").done((response) => {
            populatePinSettings(response);
        })

    ]).then(() => {
    }).catch((response) => {
        new Toast(JSON.stringify(response, null, '\t')).error();
    });
}

/**
 * Populate general settings with config values.
 * @param {Object} settings
 */
function populateGeneralSettings(settings) {
    Object.entries(settings).forEach(([key, value]) => {
        if ($("#" + key).attr('type') == 'checkbox') {
            $("#" + key).prop('checked', value);
        } else if ($("#" + key).prop("tagName") == "SELECT") {
            const optionExists = $("#" + key).find(`option[value='${value}']`).length > 0;
            if (optionExists) {
                $("#" + key).val(value);
            }
        } else if (key == "device_groups") {
            tagin.addTag(value);
        } else {
            $("#" + key).val(value);
        }
    });
}

/**
 * Populate PIN settings with `security.ini` values.
 * @param {Object} settings
 */
function populatePinSettings(settings) {
    $('#DASHBOARD_PIN').val(settings.DEFAULT_PIN);
    $('#PIN_LOCK_ENABLED').prop('checked', settings.USE_PIN_LOCK);
}

/**
 * Serialize general settings as JSON.
 */
 function setLocalSettings() {
    const serializedForm = $('#settingsForm .setting_input').serializeJSON({
        checkboxUncheckedValue: "false",
        customTypes: {
            port: (value) => {
                if (value === "" || value === "0" || isNaN(value)) {
                    return 8080;
                }
                return parseInt(value);
            },
            tags: () => { return tagin.getTags(); }
        }
    });

    const serializedPinForm = $('#settingsForm .pin_setting').serializeJSON({
        checkboxUncheckedValue: "false",
        customTypes: {
            pin: (value) => {
                if (value.length < 4 || isNaN(value)) {
                    return "";
                }
                return value;
            }
        }
    });

    setGeneralSettings(serializedForm);
    setPinSettings(serializedPinForm);
}

/**
 * Call API to set general settings.
 * @param {Object} settings
 */
function setGeneralSettings(settings) {
    let generalSettings = {
        "settings": settings
    };

    $.ajax({
        url: "/api/settings/general",
        type: "POST",
        data: JSON.stringify(generalSettings, null, '\t'),
        contentType: 'application/json;charset=UTF-8'
    }).done((response) => {
        console.log("General settings set successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
        new Toast("General settings saved.").success();
        $.ajax({
            url: "/api/system/groups",
            type: "PATCH",
            data: {},
            contentType: 'application/json;charset=UTF-8'
        }).done((response) => {
            console.log(JSON.stringify(response));
        });
    }).fail((xhr) => {
        console.log("Error while setting general settings. Error: " + xhr.responseText);
        new Toast("Error while saving general settings.").error();
    });
}

/**
 * Call API to set validated PIN settings.
 * @param {Object} settings
 */
function setPinSettings(settings) {
    if (!settings.DASHBOARD_PIN && settings.PIN_LOCK_ENABLED) {
        settings.PIN_LOCK_ENABLED = false;
        $("#PIN_LOCK_ENABLED").prop('checked', false);
        $("#DASHBOARD_PIN").val("");
        new Toast("PIN should be more than 4 digits long.").error();
    }

    const pinData = {
        "DEFAULT_PIN": settings.DASHBOARD_PIN,
        "USE_PIN_LOCK": settings.PIN_LOCK_ENABLED
    };

    $.ajax({
        url: "/api/auth/pin",
        type: 'POST',
        data: JSON.stringify(pinData),
        contentType: 'application/json;charset=UTF-8'
    });
}

/**
 * Call API to reset general settings to default values.
 */
function resetSettings() {
    $.ajax({
        url: "/api/settings/general",
        type: "DELETE",
        data: {},
        contentType: 'application/json;charset=UTF-8',
        success: () => {
            getLocalSettings();
            new Toast("General settings reset to default.").success();
            console.log("Settings reset successfully.");
        },
        error: (xhr) => {
            new Toast("Error while resetting settings.").error();
            console.log(xhr.responseText);
        }
    });
}

/**
 * Call API to reset PIN settings to default values.
 */
function resetPinSettings() {
    $.ajax({
        url: "/api/auth/pin",
        type: "DELETE",
        data: {},
        contentType: 'application/json;charset=UTF-8'
    });
}

/**
 * Call API to import new config file.
 */
 function importSettings() {
    let file_data = $('#configUpload').prop('files')[0];
    let form_data = new FormData();
    form_data.append('imported_config', file_data);

    $.ajax({
        url: '/api/settings/configuration/file',
        dataType: 'text',
        cache: false,
        contentType: false,
        processData: false,
        data: form_data,
        type: 'POST',
        success: function (response) {
            getLocalSettings();
            new Toast("General settings imported.").success();
            console.log(response);
        },
        error: function (xhr) {
            new Toast("Error while importing general settings. " + xhr.responseText).error();
            console.log(xhr.responseText);
        }
    });
}

$("#save_btn").on("click", () => {
    setLocalSettings();
});

$("#reset_btn").on("click", () => {
    $('#modal_reset_general').modal('show');
});

$("#reset_btn_modal").on("click", () => {
    $('#modal_reset_general').modal('hide');
    resetPinSettings();
    resetSettings();
});

$("#export_btn").on("click", () => {
    new Toast("Configuration file exported.").success();
});

$("#import_btn").on("click", () => {
    importSettings();
});

// Insert filename of imported config
$('.custom-file-input').on('change', (e) => {
    let fileName = $('#configUpload').val().split('\\').pop();
    let nextSibling = e.target.nextElementSibling;
    nextSibling.innerText = fileName;
})

// Toggle PIN visibility on hover
$("#toggle_pin_view").on("mouseover mouseleave", function (event) {
    event.preventDefault();
    let pinField = $('#DASHBOARD_PIN');
    pinField.attr('type') == 'text' ? pinField.attr('type', 'password') : pinField.attr('type', 'text');
    $('#toggle_pin_view').toggleClass("icon-eye");
    $('#toggle_pin_view').toggleClass("icon-eye-off");
});

// Tooltip descriptions for general settings
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
$('#MODIFY_GLOBAL_GROUP_TOOLTIP').attr('data-original-title', 'Add or remove group tags, which can be used to organize devices.');
