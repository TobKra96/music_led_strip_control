import { Device } from "./classes/Device.js";
import Toast from "./classes/Toast.js";


// Init and load all settings.
$(() => {

    // Allow to scroll sidebar when page is reloaded and mouse is already on top of sidebar.
    $(".navbar-content").trigger("mouseover");
    // Open "Edit Effects" sidebar dropdown when on an effect page.
    $("#effect_list").slideDown();

    // Update slider labels on change.
    $('input[type=range]').on('input', e => {
        $(`span[for='${$(e.currentTarget).attr('id')}']`).text(e.currentTarget.value);
    });

    /**
    * @type {string}
    */
    const effectIdentifier = $("#effectIdentifier").val();

    if (!jinja_devices.length) {
        new Toast('No device found. Create a new device in "Device Settings".').info();
        return;
    }

    // Create Base Group ("all_devices").
    let devicesById = {};
    jinja_devices.forEach(device => { devicesById[device.id] = device.name });
    const baseGroup = new Device({ assigned_to: devicesById, id: "all_devices", name: "All Devices" });

    // Create Devices and Groups from Jinja output.
    const devices = jinja_devices.map(d => { return new Device(d) });
    const groups = [baseGroup].concat(jinja_groups.map(g => { return new Device(g) }));

    let currentDevice = baseGroup;

    if (["effect_sync_fade"].includes(effectIdentifier)) {
        // Only allow `all_devices` for Sync Fade.
        if (!baseGroup.isCurrent) {
            const prevDevice = devices.find(d => d.isCurrent);
            $(`a[data-device_id=${prevDevice.id}`).removeClass("active");
        }
        baseGroup._activate();
        $(`a[data-device_id=${baseGroup.id}`).addClass("active");
    } else {
        currentDevice = devices.concat(groups).find(d => d.isCurrent) || baseGroup;
    }

    devices.concat(groups).forEach(item => {
        $(item.link).on('click', () => {
            currentDevice = item;
            setLocalSettings(currentDevice, effectIdentifier);
        });
    });

    $("#save_btn").on("click", () => {
        saveEffectSettings(currentDevice, effectIdentifier);
    });

    /**
     * Call API to get all effect names.
     * @return {Promise}
     */
    const checkboxPromise = () => $.ajax("/api/resources/effects").done((response) => {
        generateEffectCheckboxes("#nonMusicEffectCol", response.non_music);
        generateEffectCheckboxes("#musicEffectCol", response.music);
    });

    Promise.all([

        $.ajax("/api/resources/colors").done((response) => {
            Object.entries(response).forEach(([key, value]) => {
                $('.colors').append(`<option value="${key}">${value}</option>`);
            });
        }),

        $.ajax("/api/resources/gradients").done((response) => {
            Object.entries(response).forEach(([key, value]) => {
                $('.gradients').append(`<option value="${key}">${value}</option>`);
            });
        }),

        // Only generate checkboxes for Random Cycle effect page.
        effectIdentifier === "effect_random_cycle" ? checkboxPromise() : ""

    ]).then(() => {
        setLocalSettings(currentDevice, effectIdentifier);
    }).catch((response) => {
        // All requests finished but one or more failed.
        new Toast(JSON.stringify(response, null, '\t')).error();
    });

});

/**
 * Create effect checkboxes for the `Random Cycle` effect settings page.
 * @param {string} parentId
 * @param {Array.<string>} effects
 */
const generateEffectCheckboxes = (parentId, effects) => {
    Object.entries(effects).forEach(([effectId, effectName]) => {
        const checkbox = `
            <div class="custom-control custom-checkbox my-2">
                <input name="${effectId}:boolean" type="checkbox" class="custom-control-input setting_input" id="${effectId}">
                <label class="custom-control-label" for="${effectId}">${effectName}</label>
            </div>
        `;
        $(parentId).append(checkbox);
    });
}

/**
 * Populate effect settings with config values.
 * @param {Device} currentDevice
 * @param {string} effectIdentifier
 */
const setLocalSettings = (currentDevice, effectIdentifier) => {
    if (currentDevice.isGroup) {
        // TODO: Implement UI/UX for populating settings when a group is selected.
        // Options: load the default values, leave inputs blank, or show settings of first device.
        new Toast("Displaying effect settings for groups is not supported yet.").error();
        console.log("Not supported yet.");
        return;
    }
    currentDevice.getEffectSettings(effectIdentifier).done((response) => {
        Object.entries(response.settings).forEach(([key, value]) => {
            if ($("#" + key).attr('type') === 'checkbox') {
                $("#" + key).prop('checked', value);
            } else if ($("#" + key).hasClass('color_input')) {
                // Set RGB color and value from config
                const formattedRGB = formatRGB(value);
                $(".color_input").val(formattedRGB);
                pickr.setColor(formattedRGB);
            } else {
                $("#" + key).val(value);
            }
            // Set value for effect slider labels
            $(`span[for='${key}']`).text(value);

            $("#" + key).trigger('change');
        });
    });
}

/**
 * Call API to set effect settings.
 * @param {Device} currentDevice
 * @param {string} effectIdentifier
 */
const saveEffectSettings = (currentDevice, effectIdentifier) => {
    if (!currentDevice) return;

    if (currentDevice.isGroup) {
        // TODO: Pass group of devices to API.
        new Toast("Saving effect settings for groups is not supported yet.").error();
        console.log("Not supported yet.");
        return;
    }

    // Serialize effect settings as JSON.
    const serializedForm = $('#settingsForm .setting_input').serializeJSON({
        checkboxUncheckedValue: "false",
        customTypes: {
            rgb: (value) => { return parseRGB(value); }
        }
    });

    const data = {
        "device": currentDevice.id,
        "effect": effectIdentifier,
        "settings": serializedForm
    };

    // Save effect settings to config.
    $.ajax({
        url: "/api/settings/effect",
        type: "POST",
        data: JSON.stringify(data, null, '\t'),
        contentType: 'application/json;charset=UTF-8'
    }).done(response => {
        console.log("Effect settings set successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
        new Toast("Effect settings saved.").success();
    }).fail(response => {
        console.log("Error while setting effect settings. Error: " + response.responseText);
        new Toast("Error while saving effect settings.").error();
    });
}

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

    // Parse and validate RGB value when typing.
    $(input).on('input', () => {
        const formattedRGB = formatRGB(validateRGB(parseRGB(input.value)));
        parent.style.background = formattedRGB;
        pickr.setColor(formattedRGB);
    });
}

/**
 * Parse "rgb(r,g,b)" into [r,g,b].
 * @param {string} rgb
 * @return {Array.<number>}
 */
function parseRGB(rgb) {
    rgb = rgb.replace(/[^\d,]/g, '').split(',');
    return [parseInt(rgb[0]), parseInt(rgb[1]), parseInt(rgb[2])];
}

/**
 * Validate if [r,g,b] is a valid RGB value.
 * @param {Array.<number>} rgb
 * @return {Array.<number>}
 */
function validateRGB(rgb) {
    if (rgb[0] > 255 || rgb[0] < 0 || isNaN(rgb[0])) {
        rgb[0] = 0;
    }
    if (rgb[1] > 255 || rgb[1] < 0 || isNaN(rgb[1])) {
        rgb[1] = 0;
    }
    if (rgb[2] > 255 || rgb[2] < 0 || isNaN(rgb[2])) {
        rgb[2] = 0;
    }
    return rgb;
}

/**
 * Format [r,g,b] into "rgb(r,g,b)".
 * @param {Array.<number>} rgb
 * @return {string}
 */
function formatRGB(rgb) {
    return 'rgb(' + [rgb[0], rgb[1], rgb[2]].join(',') + ')';
}
