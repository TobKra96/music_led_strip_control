var devices;
var activeEffect = "";
var currentDevice = "all_devices";

// Init and load all settings
$(document).ready(function () {
    GetDevices();
});

function GetDevices() {
    $.ajax({
        url: "/GetDevices",
        type: "GET",
        success: function (response) {
            ParseDevices(response);
        },
        error: function (xhr) {
            // Handle error
        }
    });
}

function ParseDevices(devices) {
    this.currentDevice = "all_devices";
    this.devices = devices;

    this.BuildDeviceTab();
    this.AddEventListeners();
    this.UpdateCurrentDeviceText();
    this.clearAllActiveEffects();
}

function GetActiveEffect(device) {
    $.ajax({
        url: "/GetActiveEffect",
        type: "GET",
        data: {
            "device": device
        },
        success: function (response) {
            ParseActiveEffect(response);
        },
        error: function (xhr) {
            // Handle error
        }
    });
}

function ParseActiveEffect(respond) {
    this.activeEffect = respond["effect"];
    this.UpdateActiveEffectTile();
}

function SetActiveEffect(newActiveEffect) {
    var lastEffect = this.activeEffect;
    this.activeEffect = newActiveEffect;

    if (this.currentDevice == "all_devices") {
        var data = {};
        data["effect"] = this.activeEffect;

        $.ajax({
            url: "/SetActiveEffectForAll",
            type: "POST",
            data: JSON.stringify(data, null, '\t'),
            contentType: 'application/json;charset=UTF-8',
            success: function (response) {
                console.log("Effect set successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
            },
            error: function (xhr) {
                console.log("Error while setting effect. Error: " + xhr.responseText);
            }
        });

    } else {
        var data = {};
        data["device"] = this.currentDevice;
        data["effect"] = this.activeEffect;

        $.ajax({
            url: "/SetActiveEffect",
            type: "POST",
            data: JSON.stringify(data, null, '\t'),
            contentType: 'application/json;charset=UTF-8',
            success: function (response) {
                console.table("Effect set successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
            },
            error: function (xhr) {
                console.log("Error while setting effect. Error: " + xhr.responseText);
            }
        });
    }

    this.UpdateActiveEffectTile();
}


/* Device Handling */

function BuildDeviceTab() {
    var devices = this.devices;

    $('#deviceTabID').append("<li class='nav-item device_item'><a class='nav-link active' id='all_devices' data-toggle='pill' href='#pills-0' role='tab' aria-controls='pills-0' aria-selected='false'>All Devices</a></li>");

    Object.keys(devices).forEach(device_key => {
        $('#deviceTabID').append("<li class='nav-item device_item'><a class='nav-link' id=\"" + device_key + "\" data-toggle='pill' href='#pills-0' role='tab' aria-controls='pills-0' aria-selected='false'>" + devices[device_key] + "</a></li>");
    });

    $('#device_count').text(Object.keys(devices).length);
}

function AddEventListeners() {
    var elements = document.getElementsByClassName("device_item");

    for (var i = 0; i < elements.length; i++) {
        elements[i].addEventListener('click', function (e) {
            SwitchDevice(e);
        });
    }
}

function UpdateCurrentDeviceText() {
    var text = "";

    if (this.currentDevice == "all_devices") {
        text = "All Devices";
    } else {
        text = this.devices[this.currentDevice];
    }

    $("#selected_device_txt").text(text);
}

function UpdateActiveEffectTile() {
    if (this.activeEffect != "") {
        this.clearAllActiveEffects();
        this.setActiveStyle(this.activeEffect);
    }
}

function SwitchDevice(e) {
    var newDeviceId = e.target.id;
    this.currentDevice = newDeviceId;

    if (newDeviceId == "all_devices") {
        this.clearAllActiveEffects();
        this.UpdateCurrentDeviceText();
        return;
    }

    this.GetActiveEffect(newDeviceId);
    this.UpdateCurrentDeviceText();
}


/* Effect Handling */

function clearAllActiveEffects() {
    $(".dashboard_effect_active").removeClass("dashboard_effect_active");
}

function setActiveStyle(currentEffect) {
    $("#" + currentEffect).addClass("dashboard_effect_active");
}

// Listen for effect change on click
document.getElementById("dashboard-item-list").addEventListener("click", function (e) {
    switchEffect(e);
});


function switchEffect(e) {
    var newActiveEffect = "";
    var BreakException = {};

    try {
        e.path.forEach(element => {
            if (element.classList != null) {
                if (element.classList.contains("dashboard_effect")) {
                    newActiveEffect = element.id;
                    throw BreakException;
                }
            }
        });
    }
    catch (e) {
        if (e !== BreakException) throw e;
    }

    if (newActiveEffect.length > 0) {
        console.log(newActiveEffect + " was clicked.");
        SetActiveEffect(newActiveEffect);
    }
}
