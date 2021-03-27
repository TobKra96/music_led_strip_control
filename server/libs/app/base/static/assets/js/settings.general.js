var settingsIdentifier;
var effectIdentifier;
var localSettings = {};
var currentDevice;
var colors = {};
var gradients = {};

var devicesLoading = true;
var loggingLevelsLoading = true;

// Init and load all settings
$(document).ready(function () {
    $("#device_dropdown").hide();
    settingsIdentifier = $("#settingsIdentifier").val();

    GetLoggingLevels();
});

//Check if all initial ajax requests are finished.
function CheckIfFinishedInitialLoading() {
    if (!loggingLevelsLoading) {
        GetLocalSettings();
    }
}

// Get LED Strips   -----------------------------------------------------------

function GetLoggingLevels() {
    $.ajax({
        url: "/GetLoggingLevels",
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
    var context = this;
    this.logging_levels = response;

    $('.logging_levels').each(function () {
        var logging_levels = context.logging_levels;
        for (var currentKey in logging_levels) {
            var newOption = new Option(logging_levels[currentKey], currentKey);
            $(newOption).html(logging_levels[currentKey]);
            $(this).append(newOption);
        }
    });

    loggingLevelsLoading = false;
    CheckIfFinishedInitialLoading();
}


function GetGeneralSetting(setting_key) {
    $.ajax({
        url: "/GetGeneralSetting",
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
        type: 'GET',
        url: "/GetPinSetting",
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
        if (setting_value) {
            $("#" + setting_key).click();
        }
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
        url: "/SetGeneralSetting",
        type: "POST",
        data: JSON.stringify(data, null, '\t'),
        contentType: 'application/json;charset=UTF-8',
        success: function (response) {
            console.log("General settings set successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
        },
        error: function (xhr) {
            console.log("Error while setting general settings. Error: " + xhr.responseText);
        }
    });
}

function SetPinSetting() {
    var pin = $('#DASHBOARD_PIN').val();
    var pinCheckbox = false;
    if ($('#PIN_LOCK_ENABLED').is(':checked')) {
        pinCheckbox = true;
    }
    var pinData = {};
    pinData["DEFAULT_PIN"] = pin;
    pinData["USE_PIN_LOCK"] = pinCheckbox;

    $.ajax({
        type: 'POST',
        url: "/SetPinSetting",
        data: JSON.stringify(pinData),
        contentType: 'application/json;charset=UTF-8',
    });
}

function SetLocalSettings() {
    var all_setting_keys = GetAllSettingKeys();
    settings = {};

    Object.keys(all_setting_keys).forEach(setting_id => {
        var setting_key = all_setting_keys[setting_id];
        var setting_value = "";

        if ($("#" + setting_key).length) {
            if ($("#" + setting_key).attr('type') == 'checkbox') {
                setting_value = $("#" + setting_key).is(':checked')
            } else if ($("#" + setting_key).attr('type') == 'number') {
                setting_value = parseFloat($("#" + setting_key).val());
            } else {
                setting_value = $("#" + setting_key).val();
            }
        }

        settings[setting_key] = setting_value;
    })

    SetGeneralSetting(settings)
    SetPinSetting()
}

function ResetSettings() {
    var data = {};

    $.ajax({
        url: "/ResetSettings",
        type: "POST",
        data: JSON.stringify(data, null, '\t'),
        contentType: 'application/json;charset=UTF-8',
        success: function (response) {
            console.log("Reset settings successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
            location.reload();
        },
        error: function (xhr) {
            console.log("Reset settings got an error. Error: " + xhr.responseText);
        }
    });
}

document.getElementById("save_btn").addEventListener("click", function (e) {
    SetLocalSettings();
});

document.getElementById("reset_btn").addEventListener("click", function (e) {
    if (confirm('Are you sure you want to reset the config to default settings?\nA restart will be required for changes to take effect.')) {
        ResetSettings(currentDevice);
    }
});