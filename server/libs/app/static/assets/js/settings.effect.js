import { initPickr, formatRGB, parseRGB } from './classes/Pickr.js';
import { Device } from './classes/Device.js';
import Toast from './classes/Toast.js';


// Init and load all settings.
$(() => {
    // Allow to scroll sidebar when page is reloaded and mouse is already on top of sidebar.
    $('.navbar-content').trigger('mouseover');

    $('#effect_list').slideDown();

    if (!jinja_devices.length) {
        new Toast('No devices found. Create a new device in "Device Settings".', true).info();
        $('#save_btn').prop('disabled', true);
        return;
    }

    // Init Pickr if available.
    if (window.Pickr) {
        initPickr('#color_picker', '.color_input');
    }

    /**
     * Effect ID from effect page.
     * @type {string}
     */
    const effectIdentifier = $('#effectIdentifier').val();

    // Create Base Group ('all_devices').
    const devicesById = jinja_devices.reduce((obj, device) => {
        obj[device.id] = device.name;
        return obj;
    }, {});
    const baseGroup = new Device({ assigned_to: devicesById, id: 'all_devices', name: 'All Devices' });

    // Create Devices and Groups from Jinja output.
    const devices = jinja_devices.map(d => new Device(d));
    const groups = [baseGroup, ...jinja_groups.map(g => new Device(g))];

    /** Device manager to keep track of the current device. */
    const dm = {
        /** @return {Device | null} */
        get current() {
            return this._current;
        },

        /** @param {Device} device */
        set current(device) {
            this._current = device;
        }
    };

    if (['effect_sync_fade'].includes(effectIdentifier)) {
        // Only allow `all_devices` for Sync Fade.
        baseGroup._activate();
        dm.current = baseGroup;
        $(`a[data-device-id=${baseGroup.id}`).tab('show');
    } else {
        dm.current = [...devices, ...groups].find(d => d.isCurrent) || baseGroup;
    }

    /**
     * Create effect checkboxes for the `Random Cycle` effect settings page.
     * @param {string} parentId
     * @param {Array.<string>} effects
     */
    const _createEffectCheckboxes = (parentId, effects) => {
        $.each(effects, (effectId, effectName) => {
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
     * Call API to get all effect names.
     * @return {Promise}
     */
    const checkboxPromise = () => $.ajax('/api/resources/effects').done((response) => {
        _createEffectCheckboxes('#nonMusicEffectCol', response.non_music);
        _createEffectCheckboxes('#musicEffectCol', response.music);
    });

    /**
     * Populate effect settings with config values.
     */
    const setLocalSettings = () => {
        if (dm.current.isGroup) {
            // TODO: Implement UI/UX for populating settings when a group is selected.
            // Options: load the default values, leave inputs blank, or show settings of first device.
            new Toast('Displaying effect settings for groups is not supported yet.').error();
            console.log('Not supported yet.');

            // Reset form, slider labels and color picker to default values for now.
            $('#settingsForm').get(0).reset();
            $('#settingsForm span.badge').text('');
            $('#color_picker').css('background-color', 'rgb(255, 255, 255)');
            return;
        }

        dm.current.getEffectSettings(effectIdentifier).then((response) => {
            $.each(response.settings, (key, value) => {
                const el = $(`#${key}`);
                if (el.is(':checkbox')) {
                    el.prop('checked', value);
                } else if (el.is("[type='range']")) {
                    el.val(value);
                    $(`span[for='${key}']`).text(value);
                } else if (el.hasClass('color_input')) {
                    $('.color_input').val(formatRGB(value));
                } else {
                    el.val(value);
                }
                el.trigger('change');
            });
        });
    }

    /**
     * Call API to set effect settings.
     */
    const saveEffectSettings = () => {
        if (!dm.current) return;

        if (dm.current.isGroup) {
            // TODO: Pass group of devices to API.
            new Toast('Saving effect settings for groups is not supported yet.').error();
            console.log('Not supported yet.');
            return;
        }

        // Serialize effect settings as JSON.
        const serializedForm = $('#settingsForm .setting_input').serializeJSON({
            checkboxUncheckedValue: 'false',
            customTypes: {
                rgb: (value) => { return parseRGB(value); }
            }
        });

        const data = {
            device: dm.current.id,
            effect: effectIdentifier,
            settings: serializedForm
        };

        // Save effect settings to config.
        $.ajax({
            url: '/api/settings/effect',
            type: 'POST',
            data: JSON.stringify(data),
            contentType: 'application/json;charset=UTF-8'
        }).done((data) => {
            console.log(`Effect settings set successfully. Response:\n\n${JSON.stringify(data, null, '\t')}`);
            new Toast('Effect settings saved.').success();
        }).fail((data) => {
            console.log(`Error while setting effect settings. Error:\n\n${data.responseText}`);
            new Toast('Error while saving effect settings.').error();
        });
    }

    const promises = [  // Preload dropdown values and checkboxes.

        $.ajax('/api/resources/colors').done((response) => {
            $.each(response, (key, value) => {
                $('.colors').append(`<option value="${key}">${value}</option>`);
            });
        }),

        $.ajax('/api/resources/gradients').done((response) => {
            $.each(response, (key, value) => {
                $('.gradients').append(`<option value="${key}">${value}</option>`);
            });
        }),

        // Only generate checkboxes for Random Cycle effect page.
        'effect_random_cycle' === effectIdentifier ? checkboxPromise() : null,

    ];

    Promise.all(promises).then(() => {
        setLocalSettings();
    }).catch((data) => {
        // All requests finished but one or more failed.
        console.log(data);
        new Toast('Error while loading effect settings.').error();
    });

    [...devices, ...groups].forEach(item => {
        $(item.link).on('click', () => {
            dm.current = item;
            setLocalSettings();
        });
    });

    // Update slider labels on change.
    $('input[type=range]').on('input', e => {
        $(`span[for='${$(e.currentTarget).attr('id')}']`).text(e.currentTarget.value);
    });

    $('#save_btn').on('click', () => {
        saveEffectSettings();
    });

});
