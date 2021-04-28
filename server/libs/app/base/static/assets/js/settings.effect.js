import Device from "./classes/Device.js";
import Toast from "./classes/Toast.js";

let currentDevice = undefined;
let effectIdentifier = "";

// Init and load all settings
$(function () {

    // Allow to scroll sidebar when page is reloaded and mouse is already on top of sidebar
    $(".navbar-content").trigger("mouseover");

    // Open "Edit Effects" sidebar dropdown when on an effect page
    $("#effect_list").slideDown();

    effectIdentifier = $("#effectIdentifier").val();

    if (!jinja_devices.length) {
        new Toast('No device found. Create a new device in "Device Settings".').info()
    } else {
        // Start with Fake Device & create Devices from Jinja output
        const fake_device = [new Device({ id: "all_devices", name: "All Devices" })];

        // Only allow all_devices for sync fade effect
        if (effectIdentifier == "effect_sync_fade") {
            localStorage.setItem('lastDevice', fake_device[0].id);
        }

        const devices = fake_device.concat(jinja_devices.map(d => { return new Device(d) }));

        if (effectIdentifier == "effect_sync_fade") {
            devices[0]._activate();
            $(`a[data-device_id=${devices[0].id}`).addClass("active");
            currentDevice = devices[0];
        } else {
            currentDevice = devices.find(d => d.isCurrent === true);
        }

        devices.forEach(device => {
            device.link.addEventListener('click', () => {
                currentDevice = device;
                SetLocalSettings();
            });
        });

        Promise.all([

            $.ajax("/GetColors").done((response) => {
                $('.colors').each(function () {
                    for (var currentKey in response) {
                        var newOption = new Option(currentKey, currentKey);
                        // jquerify the DOM object 'o' so we can use the html method
                        $(newOption).html(currentKey);
                        $(this).append(newOption);
                    }
                });
            }),

            $.ajax("/GetGradients").done((response) => {
                $('.gradients').each(function () {
                    for (var currentKey in response) {
                        var newOption = new Option(currentKey, currentKey);
                        /// jquerify the DOM object 'o' so we can use the html method
                        $(newOption).html(currentKey);
                        $(this).append(newOption);
                    }
                });
            })

        ]).then(response => {
            SetLocalSettings();
        }).catch((response) => {
            // all requests finished but one or more failed
            new Toast(JSON.stringify(response, null, '\t')).error();
        });
    }

});


function GetAllSettingKeys() {
    return $(".setting_input").map(function () { return this.id })
        .toArray();
}

function SetLocalSettings() {
    const all_setting_keys = GetAllSettingKeys();

    all_setting_keys.map((setting) => {
        currentDevice.getEffectSetting(effectIdentifier, setting).then((response) => {
            const setting_key = response["setting_key"];
            const setting_value = response["setting_value"];

            if ($("#" + setting_key).attr('type') == 'checkbox') {
                $("#" + setting_key).prop('checked', setting_value);
            } else if ($("#" + setting_key).hasClass('color_input')) {
                // Set RGB color and value from config
                const formattedRGB = formatRGB(setting_value);
                $(".color_input").val(formattedRGB);
                pickr.setColor(formattedRGB);
            } else {
                $("#" + setting_key).val(setting_value);
            }

            $("#" + setting_key).trigger('change');

            // Set initial effect slider values
            $("span[for='" + setting_key + "']").text(setting_value);
        });
    });
}

/* Device Handling */

$("#save_btn").on("click", function () {
    const settings = {};
    const all_setting_keys = GetAllSettingKeys();

    all_setting_keys.map((setting_key) => {
        let setting_value = "";

        if ($("#" + setting_key).length) {
            if ($("#" + setting_key).attr('type') == 'checkbox') {
                setting_value = $("#" + setting_key).is(':checked');
            } else if ($("#" + setting_key).attr('type') == 'number') {
                setting_value = parseFloat($("#" + setting_key).val());
            } else if ($("#" + setting_key).attr('type') == 'range') {
                setting_value = parseFloat($("#" + setting_key).val());
            } else if ($("#" + setting_key).hasClass('color_input')) {
                // Save RGB value to config
                setting_value = parseRGB($(".color_input").val());
            } else {
                setting_value = $("#" + setting_key).val();
            }
        }

        settings[setting_key] = setting_value;
    })

    const data = {
        "device": currentDevice.id,
        "effect": effectIdentifier,
        "settings": settings
    };

    $.ajax({
        url: "/SetEffectSetting",
        type: "POST",
        data: JSON.stringify(data, null, '\t'),
        contentType: 'application/json;charset=UTF-8'
    }).done(response => {
        // todo toasts
        console.log("Effect settings set successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
    }).fail(response => {
        // todo toasts
        console.log("Error while setting effect settings. Error: " + response.responseText);
    });
});

// Set effect slider values
$('input[type=range]').on('input', function () {
    $("span[for='" + $(this).attr('id') + "']").text(this.value);
});

// Create color picker instance
const parent = document.querySelector('#color_picker');
const input = document.querySelector('.color_input');

if (parent && input) {
    var pickr = Pickr.create({
        el: parent,
        theme: 'monolith',
        default: 'rgb(255,255,255)',
        position: 'left-middle',
        lockOpacity: false,
        comparison: false,
        useAsButton: true,

        swatches: [
            'rgb(244, 67, 54)',
            'rgb(233, 30, 99)',
            'rgb(156, 39, 176)',
            'rgb(103, 58, 183)',
            'rgb(63, 81, 181)',
            'rgb(33, 150, 243)',
            'rgb(3, 169, 244)',
            'rgb(0, 188, 212)',
            'rgb(0, 150, 136)',
            'rgb(76, 175, 80)',
            'rgb(139, 195, 74)',
            'rgb(205, 220, 57)',
            'rgb(255, 235, 59)',
            'rgb(255, 193, 7)'
        ],

        components: {
            hue: true
        }
    }).on('init', pickr => {
        const newColor = pickr.getSelectedColor().toRGBA().toString(0).replace(', 1)', ')').replace('rgba', 'rgb');
        parent.style.background = newColor;
        input.value = newColor;
    }).on('change', color => {
        const newColor = color.toRGBA().toString(0).replace(', 1)', ')').replace('rgba', 'rgb');
        parent.style.background = newColor;
        input.value = newColor;
    })

    // Parse and validate RGB value when typing
    input.addEventListener('input', () => {
        const formattedRGB = formatRGB(validateRGB(parseRGB(input.value)));
        parent.style.background = formattedRGB;
        pickr.setColor(formattedRGB);
    });
}

/** Parse "rgb(r,g,b)" into [r,g,b] **/
function parseRGB(rgb) {
    rgb = rgb.replace(/[^\d,]/g, '').split(',');
    return [parseInt(rgb[0]), parseInt(rgb[1]), parseInt(rgb[2])];
}

/** Validate if [r,g,b] is a valid RGB value **/
function validateRGB(rgb) {
    if (rgb[0] > 255 || rgb[0] < 0 || isNaN(rgb[0])) {
        rgb[0] = 0;
    };
    if (rgb[1] > 255 || rgb[1] < 0 || isNaN(rgb[1])) {
        rgb[1] = 0;
    };
    if (rgb[2] > 255 || rgb[2] < 0 || isNaN(rgb[2])) {
        rgb[2] = 0;
    };
    return rgb;
}

/** Format [r,g,b] into "rgb(r,g,b)" **/
function formatRGB(rgb) {
    return 'rgb(' + [rgb[0], rgb[1], rgb[2]].join(',') + ')';
}
