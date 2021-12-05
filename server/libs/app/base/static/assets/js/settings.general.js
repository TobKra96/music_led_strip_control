import Toast from "./classes/Toast.js";
import Tagin from "../plugins/tagin/js/tagin.js";

var settingsIdentifier;
var localSettings = {};
var currentDevice;
var tagin;

var loggingLevelsLoading = true;
var audioDevicesLoading = true;

// Init and load all settings
$(document).ready(function () {
    $("#settings_list").slideDown();
    $("#device_dropdown").hide();
    settingsIdentifier = $("#settingsIdentifier").val();
    var options = {
        separator: ',',
        duplicate: false,
        enter: true,
        transform: input => input,
        placeholder: 'Add a group...'
    };
    tagin = new Tagin(document.querySelector(".tagin"), options);

    GetLoggingLevels();
    GetAudioDevices();
});

//Check if all initial ajax requests are finished.
function CheckIfFinishedInitialLoading() {
    if (!loggingLevelsLoading && !audioDevicesLoading) {
        GetLocalSettings();
    }
}

// Get LED Strips   -----------------------------------------------------------

function GetLoggingLevels() {
    $.ajax({
        url: "/api/resources/logging-levels",
        type: "GET",
        data: {},
        success: function (response) {
            ParseGetLoggingLevels(response);
        },
        error: function (xhr) {
            // Handle error
        }
    });
}

function ParseGetLoggingLevels(response) {
    let logging_levels = response;

    $('.logging_levels').each(function () {
        for (var currentKey in logging_levels) {
            var newOption = new Option(logging_levels[currentKey], currentKey);
            $(newOption).html(logging_levels[currentKey]);
            $(this).append(newOption);
        }
    });

    loggingLevelsLoading = false;
    CheckIfFinishedInitialLoading();
}


// Get Audio Devices  -----------------------------------------------------------

function GetAudioDevices() {
    $.ajax({
        url: "/api/resources/audio-devices",
        type: "GET",
        data: {},
        success: function (response) {
            ParseGetAudioDevices(response);
        },
        error: function (xhr) {
            // Handle error
        }
    });
}

function ParseGetAudioDevices(response) {
    let audio_devices = response;

    $('.audio_devices').each(function () {
        for (var currentKey in audio_devices) {
            var newOption = new Option(audio_devices[currentKey], currentKey);
            $(newOption).html(audio_devices[currentKey]);
            $(this).append(newOption);
        }
    });

    audioDevicesLoading = false;
    CheckIfFinishedInitialLoading();
}


function GetGeneralSetting(setting_key) {
    $.ajax({
        url: "/api/settings/general",
        type: "GET",
        data: {
            "setting_key": setting_key,
        },
        success: function (response) {
            ParseGetGeneralSetting(response);
        },
        error: function (xhr) {
            // Handle error
        }
    });
}

function ParseGetGeneralSetting(response) {
    var setting_key = response["setting_key"];
    var setting_value = response["setting_value"];
    localSettings[setting_key] = setting_value;

    SetLocalInput(setting_key, setting_value)
}

function GetPinSetting() {
    $.ajax({
        url: "/api/auth/pin",
        type: 'GET',
        contentType: 'application/json;charset=UTF-8',
        success: function (response) {
            ParseGetPinSetting(response)
        },
    });
}

function ParseGetPinSetting(response) {
    var pin = response["DEFAULT_PIN"];
    var use_pin_lock = response["USE_PIN_LOCK"];

    $('#DASHBOARD_PIN').val(pin);
    $('#PIN_LOCK_ENABLED').prop('checked', use_pin_lock);
}

function GetLocalSettings() {
    var all_setting_keys = GetAllSettingKeys();

    Object.keys(all_setting_keys).forEach(setting_id => {
        GetGeneralSetting(all_setting_keys[setting_id])
    })
    GetPinSetting()
}

function SetLocalInput(setting_key, setting_value) {
    if ($("#" + setting_key).attr('type') == 'checkbox') {
        $("#" + setting_key).prop('checked', setting_value);
    } else if (setting_key == "device_groups") {
        tagin.addTag(false, setting_value.join(","))
    } else {
        $("#" + setting_key).val(setting_value);
    }

    $("#" + setting_key).trigger('change');
}


function GetAllSettingKeys() {
    var all_setting_keys = $(".setting_input").map(function () {
        return this.attributes["id"].value;
    }).get();

    return all_setting_keys;
}


function SetGeneralSetting(settings) {
    var data = {};
    data["settings"] = settings;

    $.ajax({
        url: "/api/settings/general",
        type: "POST",
        data: JSON.stringify(data, null, '\t'),
        contentType: 'application/json;charset=UTF-8'
    }).done(function (response) {
        console.log("General settings set successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
        new Toast("General settings saved.").success();
        $.ajax({
            url: "/api/system/groups",
            type: "PATCH",
            data: {},
            contentType: 'application/json;charset=UTF-8'
        }).done(function (response) {
            console.log(JSON.stringify(response));
        });
    }).fail(function (xhr) {
        console.log("Error while setting general settings. Error: " + xhr.responseText);
        new Toast("Error while saving general settings.").error();
    });
}

function SetPinSetting() {
    var pin = $('#DASHBOARD_PIN').val();
    var pinCheckbox = false;
    if ($('#PIN_LOCK_ENABLED').is(':checked')) {
        pinCheckbox = true;
    }
    if (pin.length < 4) {
        pin = ""
        pinCheckbox = false;
        $('#PIN_LOCK_ENABLED').prop('checked', pinCheckbox);
        $('#DASHBOARD_PIN').val(pin);
    }
    var pinData = {};
    pinData["DEFAULT_PIN"] = pin;
    pinData["USE_PIN_LOCK"] = pinCheckbox;

    $.ajax({
        url: "/api/auth/pin",
        type: 'POST',
        data: JSON.stringify(pinData),
        contentType: 'application/json;charset=UTF-8',
    });
}

function SetLocalSettings() {
    var all_setting_keys = GetAllSettingKeys();
    let settings = {};

    Object.keys(all_setting_keys).forEach(setting_id => {
        var setting_key = all_setting_keys[setting_id];
        var setting_value = "";

        if ($("#" + setting_key).length) {
            if ($("#" + setting_key).attr('type') == 'checkbox') {
                setting_value = $("#" + setting_key).is(':checked')
            } else if ($("#" + setting_key).attr('type') == 'number') {
                setting_value = parseFloat($("#" + setting_key).val());
                if (setting_key == "webserver_port" && isNaN(setting_value)) {
                    setting_value = 8080;
                }
            } else if (setting_key == "device_groups") {
                setting_value = tagin.getTags()
            } else {
                setting_value = $("#" + setting_key).val();
            }
        }

        settings[setting_key] = setting_value;
    })

    SetGeneralSetting(settings);
    SetPinSetting();
}

function ResetSettings() {
    var data = {};

    $.ajax({
        url: "/api/settings/general",
        type: "DELETE",
        data: JSON.stringify(data, null, '\t'),
        contentType: 'application/json;charset=UTF-8',
        success: function (response) {
            console.log("Settings reset successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
            location.reload();
        },
        error: function (xhr) {
            console.log("Error while resetting settings. Error: " + xhr.responseText);
        }
    });
}

function ResetPinSettings() {
    $.ajax({
        url: "/api/auth/pin",
        type: "DELETE",
        data: {},
        contentType: 'application/json;charset=UTF-8',
        success: function (response) {
            ParseGetPinSetting(response)
        },
    });
}

$("#save_btn").on("click", function () {
    SetLocalSettings();
});

$("#reset_btn").on("click", function () {
    $('#modal_reset_general').modal('show')
});

$("#reset_btn_modal").on("click", function () {
    $('#modal_reset_general').modal('hide')
    ResetPinSettings();
    ResetSettings();
});

$("#export_btn").on("click", function () {
    new Toast("Configuration file exported.").success();
});

$("#import_btn").on("click", function () {
    ImportSettings();
});

function ImportSettings() {
    var file_data = $('#configUpload').prop('files')[0];
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
            location.reload();
        },
        error: function (xhr) {
            location.reload();
        }
    });
}

// Insert filename of imported config
$('.custom-file-input').on('change', (e) => {
    let fileName = $('#configUpload').val().split('\\').pop();
    let nextSibling = e.target.nextElementSibling;
    nextSibling.innerText = fileName;
})

// Toggle PIN visibility on hover
$("#toggle_pin_view").on("mouseover mouseleave", function (event) {
    event.preventDefault();
    let pinField = $('#DASHBOARD_PIN')
    pinField.attr('type') == 'text' ? pinField.attr('type', 'password') : pinField.attr('type', 'text')
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
