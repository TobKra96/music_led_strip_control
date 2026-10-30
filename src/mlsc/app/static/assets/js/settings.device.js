import { api } from './classes/Api.js';
import { Device, tagin } from './classes/Device.js';
import { waitForOperation } from './classes/Operation.js';
import { splitForm } from './classes/OutputSetup.js';
import SetupWizard from './classes/SetupWizard.js';
import Toast from './classes/Toast.js';
import UnsavedChanges from './classes/UnsavedChanges.js';


// Init and load all settings.
$(() => {
    // Allow to scroll sidebar when page is reloaded and mouse is already on top of sidebar.
    $('.navbar-content').trigger('mouseover');

    $('#settings_list').slideDown();
    $(tagin.input).attr({ list: 'device_group_options', placeholder: 'Add a group' });

    let outputTypes = {};

    const unsaved = new UnsavedChanges(document.getElementById('settingsForm'));

    const wizard = new SetupWizard({
        getOutputTypes: () => outputTypes,
        getGroups: () => jinja_groups.groups,
        getDeviceNames: id => devices.filter(d => d.id !== id).map(d => d.name),
        onApplied: (name) => {
            dm.current.name = name;
            $('#selected_device_txt').text(name);
            dm.select(dm.current);
        },
    });

    // Preload dropdown values.
    const optionsLoaded = api.get('/resources/output-types').then((data) => {
        outputTypes = data;
        $.each(data, (key, value) => {
            $('.output_type').append(`<option value='${key}'>${value}</option>`);
        });
    });

    /** @type {Array.<Device>} */
    let devices = jinja_devices.map(d => new Device(d));

    /** Device manager to keep track of the current device. */
    const dm = {
        _selection: 0,

        /** @return {Device | null} */
        get current() {
            return this._current;
        },

        /**
         * Make the device current and show its settings. The form counts as saved once it is populated.
         * @param {Device | null} device
         * @return {Promise}
         */
        select(device) {
            this._current = device;
            const selection = ++this._selection;
            if (!device) return Promise.resolve();
            // Only the latest selection may mark the form clean, and a failed load leaves it as it is.
            return device.refreshConfig(optionsLoaded)
                .then(() => selection === this._selection && unsaved.markClean())
                .catch(() => { });
        }
    };

    dm._current = devices.find(d => d.id === localStorage.getItem('lastDevice')) || devices[0] || null;

    optionsLoaded.then(() => {

        if (!jinja_devices.length) {
            $('#noDeviceFound').removeClass('d-none');
            return;
        }

        $('#deviceFound').removeClass('d-none');

        // Get device id from URL parameters.
        const urlParams = new URLSearchParams(window.location.search);
        const selectedDevice = devices.find(device => device.id === urlParams.get('id'));
        if (selectedDevice) {
            dm._current = selectedDevice;
        }
        const loaded = dm.select(dm.current);

        $('#selected_device_txt').text(dm.current.name);
        $(`a[data-device-id=${dm.current.id}`).tab('show');
        localStorage.setItem('lastDevice', dm.current.id);

        // Add behavior to device bar.
        devices.forEach(device => {
            $(device.link).on('click', () => {
                dm.select(device);
            });
        });

        // `?wizard=1` opens the Setup Wizard, for example from a link in the docs.
        if (urlParams.get('wizard') === '1') {
            loaded.then(() => wizard.open(dm.current.id)).catch(() => {});
        }

        return loaded;
    }).catch((error) => {
        new Toast(`Error while loading settings. ${error.summary}`).error();
    });

    /**
     * Call API to create new default device.
     */
    const createDevice = () => {
        if (!unsaved.guard()) return;

        api.post('/devices').then((/** @type {DeviceFromApi} */ data) => {
            const newDevice = new Device(data);
            devices.push(newDevice);

            dm.select(newDevice);
            localStorage.setItem('lastDevice', dm.current.id);

            _reloadDeviceBar(devices);

            new Toast(`Device '${dm.current.name}' created.`).success();
            // A new Device starts with the defaults, so walk through its setup right away.
            wizard.open(newDevice.id).catch(() => {});
        }).catch((error) => {
            new Toast(`Error while creating new device. ${error.summary}`).error();
        });
    }

    /**
     * Call API to delete a device.
     */
    const deleteDevice = () => {
        const deleted = dm.current;

        api.delete(`/devices/${deleted.id}`).then(() => {
            new Toast(`Device '${deleted.name}' deleted.`).success();

            devices = devices.filter(d => d.id !== deleted.id);

            if (devices.length) {
                dm.select(devices[devices.length - 1]);
                localStorage.setItem('lastDevice', dm.current.id);
            } else {
                dm.select(null);
                unsaved.markClean();
                localStorage.removeItem('lastDevice');
            }

            _reloadDeviceBar(devices);

        }).catch((error) => {
            new Toast(`Error while deleting device '${deleted.name}'. ${error.summary}`).error();
        });
    }

    /**
     * Serialize device settings to JSON.
     */
    const setLocalSettings = async () => {
        const deviceName = $('#device_name').val().trim();
        const nameExists = devices.some(d => d.name === deviceName && d.id !== dm.current.id);
        if (nameExists) {  // Do not save device settings if device name already exists.
            new Toast(`Device with the name '${deviceName}' already exists.`).error();
            return;
        }

        const serializedDeviceForm = $('#settingsForm .device_setting_input').serializeJSON({
            checkboxUncheckedValue: 'false',
            customTypes: {
                name: (value) => { return value.trim() },
                ledcount: (value) => {
                    // https://github.com/rpi-ws281x/rpi-ws281x-python/issues/70
                    if (isNaN(value) || value < 7) {
                        return 7;
                    }
                    return parseInt(value);
                },
                tags: () => { return tagin.getTagObjects(); }
            }
        });

        // The settings of every output type are saved with the device, nested under `output`.
        const output = {};
        Object.keys(outputTypes).forEach(outputType => {
            output[outputType] = $(`#settingsForm .${outputType}`).serializeJSON({
                checkboxUncheckedValue: 'false'
            });
        });

        // The strip and Output settings are applied safely: they roll back when the Output does not work.
        const { apply, save } = splitForm(serializedDeviceForm, output);
        const deviceId = dm.current.id;
        const $button = $('#save_btn').prop('disabled', true);
        try {
            const data = Object.keys(save).length ? await api.patch(`/devices/${deviceId}/settings`, save) : null;
            const operation = await waitForOperation(await api.patch(`/devices/${deviceId}/output`, apply));
            if (data) {
                dm.current.name = data.device_name;
                $('#selected_device_txt').text(data.device_name);
            }
            if (operation.state === 'confirmed') {
                unsaved.markClean();
                new Toast(`Device '${dm.current.name}' saved.`).success();
            } else {
                new Toast(`The output settings did not work and were rolled back. ${operation.error || ''}`).error();
                await dm.select(dm.current);
            }
        } catch (error) {
            new Toast(`Error while saving device '${dm.current.name}'. ${error.summary}`).error();
        } finally {
            $button.prop('disabled', false);
        }
    }

    /**
     * Update device bar with new pills.
     * @param {Array.<Device>} devices
     */
    const _reloadDeviceBar = (devices) => {
        // Remove every pill in the device bar.
        // const tabs = document.getElementById('device_tab_id');
        // tabs.innerHTML = '';

        const deviceBar = $('#device_tab_id').empty();

        // Build device bar.
        devices.forEach(device => {
            const link = device.createPill(dm.current.id);

            $(link).on('click', () => {
                dm.select(device);
                $('#selected_device_txt').text(device.name);
            });

            // tabs.appendChild(link);
            deviceBar.append(link);
        });

        $('#device_count').text(devices.length);
        $('#plural_label').text(devices.length === 1 ? '' : 's');


        if (devices.length) {
            $('#deviceFound, #selected_device_label').removeClass('d-none');
            $('#selected_device_txt').text(dm.current.name);
            $('#noDeviceFound').addClass('d-none');
        } else {
            $('#deviceFound, #selected_device_label').addClass('d-none');
            $('#selected_device_txt').text('');
            $('#noDeviceFound').removeClass('d-none');
        }
    }

    /**
     * Suggest the global groups that are not yet assigned to the device.
     */
    const _refreshGroupSuggestions = () => {
        const assigned = tagin.getTags();
        const datalist = $('#device_group_options').empty();
        $.each(jinja_groups.groups, (groupId, globalGroup) => {
            if (!assigned.includes(globalGroup)) {
                datalist.append($('<option>').val(globalGroup));
            }
        });
    }

    /**
     * Ignore characters that do not match the regex when typing.
     * @param {Event} e An `input` event.
     * @param {RegExp} regex The regex to match against.
     */
    const _filterChars = (e, regex) => {
        let position = e.currentTarget.selectionStart;
        const textVal = e.currentTarget.value;
        if (regex.test(textVal)) {
            $(e.currentTarget).val(textVal.replace(regex, ''));
            position--;
        }
        e.currentTarget.setSelectionRange(position, position);
    };

    // Ask before a pill click switches away from edited settings. Runs first, so no other handler sees a refused click.
    document.getElementById('device_tab_id').addEventListener('click', (e) => {
        const pill = e.target.closest('a[data-device-id]');
        if (pill && dm.current && pill.getAttribute('data-device-id') !== dm.current.id && !unsaved.guard()) {
            e.preventDefault();
            e.stopImmediatePropagation();
        }
    }, true);

    $('#create1_btn, #create2_btn').on('click', () => {
        createDevice();
    });

    $('#save_btn').on('click', () => {
        setLocalSettings();
    });

    $('#wizard_btn').on('click', () => {
        if (!unsaved.guard()) return;
        wizard.open(dm.current.id).catch((error) => {
            new Toast(`Could not open the Setup Wizard. ${error.summary}`).error();
        });
    });

    $('#delete_btn').on('click', () => {
        $('#modal_device_name').text(dm.current.name);
        $('#modal_delete_device').modal('show');
    });

    $('#delete_btn_modal').on('click', () => {
        $('#modal_delete_device').modal('hide');
        deleteDevice();
    })

    $('#device_name').on('input', e => {
        _filterChars(e, /[^a-zA-Zа-яА-Я0-9_ ()-]/gi);
    });

    $('#udp_client_ip').on('input', e => {
        _filterChars(e, /[^0-9.]/gi);
    });

    // Keep the suggestions in sync with the groups assigned to the device.
    $('.tagin').on('change', _refreshGroupSuggestions);

    // Add the group right away when a suggestion is picked.
    $(tagin.input).on('input', e => {
        const isPicked = !e.originalEvent.inputType || e.originalEvent.inputType === 'insertReplacementText';
        if (isPicked && tagin.resolve(tagin.input.value)) {
            tagin.appendTag(true);
        }
    });

    // Without any global groups there is nothing to pick from.
    $('#device_group_hint').toggleClass('d-none', Object.keys(jinja_groups.groups).length > 0);

    // Set LED strip brightness slider badge.
    $('input[type=range]').on('input', e => {
        $(`span[for='${$(e.currentTarget).attr('id')}']`).text(e.currentTarget.value);
    });

    // Hide unused output settings.
    $('#output_type').on('change', () => {
        if ($('#output_type').val() === 'output_raspi') {
            $('#raspberrypi').removeClass('d-none');
            $('#udp').addClass('d-none');
            return;
        }
        $('#udp').removeClass('d-none');
        $('#raspberrypi').addClass('d-none');
    });

    // Limit 'led_mid' input to be between 0 and 'led_count'.
    $('#led_mid').on('input', () => {
        const led_mid = $('#led_mid').val();
        const led_count = $('#led_count').val();
        if (parseInt(led_mid) >= parseInt(led_count)) {
            $('#led_mid').val(parseInt(led_count) - 1);
        } else if (led_mid.startsWith('0')) {
            $('#led_mid').val(led_mid.substring(1));
        }
    });

});


// Tooltip descriptions for device settings.
$('#FPS_TOOLTIP').attr('data-original-title', 'The maximum FPS you want to output with current device.<br><br>Default setting: 60');
$('#LED_Count_TOOLTIP').attr('data-original-title', 'The amount of LEDs you want to control with current device. Value should be more than 6.');
$('#LED_Mid_TOOLTIP').attr('data-original-title', 'The middle of the LED Strip.<br>If you have a corner setup, you can shift the middle. Value should be more than 0 and less than the Number of LEDs.');
$('#OUTPUT_TYPE_TOOLTIP').attr('data-original-title', 'The output type for current device.<br>Raspberry Pi can be used directly, ESP can be used as a client.<br><br>Note that only one device should be set to "Output Raspberry Pi", otherwise the LED Strip will flicker.');
$('#LED_Pin_TOOLTIP').attr('data-original-title', 'The GPIO Pin used for the signal.<br>Not all pins are compatible.<br>Use GPIO 18 (pin 12) for PWM0 and GPIO 13 (pin 33) for PWM1.<br><br>Default setting: 18');
$('#LED_Freq_Hz_TOOLTIP').attr('data-original-title', 'The signal frequency used to communicate with the LED Strip.<br><br>Default setting: 800000');
$('#LED_Channel_TOOLTIP').attr('data-original-title', 'The channel you want to use. PWM0 - 0 and PWM1 - 1.<br><br>Default setting: 0');
$('#LED_Dma_TOOLTIP').attr('data-original-title', 'The direct memory access channel. Select a channel between 0-14.<br><br>Default setting: 10');
$('#Chip_Family_TOOLTIP').attr('data-original-title', 'The LED controller chip of your strip.<br><br>Default setting: WS2812');
$('#Colour_Order_TOOLTIP').attr('data-original-title', 'The order of the colour channels your strip expects. Pick another order if red, green and blue show up swapped.<br><br>Default setting: GRB');
$('#LED_Invert_TOOLTIP').attr('data-original-title', 'The parameter for inverting the LED signal. It can be useful if you want to use an inverted logic level shifter.<br><br>Default value: Off');
$('#UDP_Client_IP_TOOLTIP').attr('data-original-title', 'The IP address of the client.');
$('#UDP_Client_Port_TOOLTIP').attr('data-original-title', 'The port used for the communication between the server and client.<br><br>Default setting: 7777');
$('#DEVICE_GROUP_TOOLTIP').attr('data-original-title', 'Device groups allow you to organize devices with custom tags.');


/**
 * @typedef {object} DeviceFromApi
 * @property {object} assigned_to
 * @property {string} id
 * @property {string} name
 */
