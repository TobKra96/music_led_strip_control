import Toast from "./classes/Toast.js";

var settingsIdentifier;
var localSettings = {};
var currentDevice;

var loggingLevelsLoading = true;
var audioDevicesLoading = true;

// Init and load all settings
$(document).ready(function () {
    $("#device_dropdown").hide();
    settingsIdentifier = $("#settingsIdentifier").val();

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
        contentType: 'application/json;charset=UTF-8',
        success: function (response) {
            console.log("General settings set successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
            new Toast("General settings saved.").success();
        },
        error: function (xhr) {
            console.log("Error while setting general settings. Error: " + xhr.responseText);
            new Toast("Error while saving general settings.").error();
        }
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

document.getElementById("save_btn").addEventListener("click", function (e) {
    SetLocalSettings();
});

document.getElementById("reset_btn").addEventListener("click", function (e) {
    $('#modal_reset_general').modal('show')
});

document.getElementById("reset_btn_modal").addEventListener("click", function (e) {
    $('#modal_reset_general').modal('hide')
    ResetPinSettings();
    ResetSettings(currentDevice);
});

$("#export_btn").on("click", function () {
    new Toast("Configuration file exported.").success();
});

document.getElementById("import_btn").addEventListener("click", function (e) {
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