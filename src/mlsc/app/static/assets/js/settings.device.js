import { Device, tagin } from './classes/Device.js';
import Toast from './classes/Toast.js';


// Init and load all settings.
$(() => {
    // Allow to scroll sidebar when page is reloaded and mouse is already on top of sidebar.
    $('.navbar-content').trigger('mouseover');

    $('#settings_list').slideDown();
    $('.tagin-input').prop('disabled', true);

    let outputTypes = {};

    const promises = [  // Preload dropdown values.

        $.ajax('/api/resources/output-types').done((data) => {
            outputTypes = data;
            $.each(data, (key, value) => {
                $('.output_type').append(`<option value='${key}'>${value}</option>`);
            });
        }),

        $.ajax('/api/resources/led-strips').done((data) => {
            $.each(data, (key, value) => {
                $('.led_strips').append(`<option value='${key}'>${value}</option>`);
            });
        })

    ]

    /** @type {Array.<Device>} */
    let devices = jinja_devices.map(d => new Device(d));

    /** Device manager to keep track of the current device. */
    const dm = {
        /** @return {Device | null} */
        get current() {
            return this._current;
        },

        /** @param {Device} device */
        set current(device) {
            this._current = device;
            if (device) device.refreshConfig();
        }
    };

    dm.current = devices.find(d => d.id === localStorage.getItem('lastDevice')) || devices[0] || null;

    Promise.all(promises).then(() => {

        if (!jinja_devices.length) {
            $('#noDeviceFound').removeClass('d-none');
            return;
        }

        $('#deviceFound').removeClass('d-none');

        // Get device id from URL parameters.
        const urlParams = new URLSearchParams(window.location.search);
        const selectedDevice = devices.find(device => device.id === urlParams.get('id'));
        if (selectedDevice) {
            dm.current = selectedDevice;
        }

        $('#selected_device_txt').text(dm.current.name);
        $(`a[data-device-id=${dm.current.id}`).tab('show');
        localStorage.setItem('lastDevice', dm.current.id);

        // Add behavior to device bar.
        devices.forEach(device => {
            $(device.link).on('click', () => {
                dm.current = device;
            });
        });

    }).catch((data) => {
        // All requests finished but one or more failed.
        console.log(data);
        new Toast('Error while loading settings.').error();
    });

    /**
     * Call API to create new default device.
     */
    const createDevice = () => {
        $.ajax({
            url: '/api/system/devices',
            type: 'POST',
            contentType: 'application/json;charset=UTF-8'
        }).done((/** @type {NewDeviceFromApi} */ data) => {
            console.log(`New device created successfully. Response:\n\n${JSON.stringify(data, null, '\t')}`);
            const newDeviceId = data.device_id;

            $.ajax('/api/system/devices').done((/** @type {Array.<DeviceFromApi>} */ data) => {
                const NewDeviceParams = data.find(d => d.id === newDeviceId);
                const newDevice = new Device(NewDeviceParams);
                devices.push(newDevice);

                dm.current = newDevice;
                localStorage.setItem('lastDevice', dm.current.id);

                _reloadDeviceBar(devices);

                new Toast(`Device '${dm.current.name}' created.`).success();
            });
        }).fail((data) => {
            console.log(`Error while creating new device. Error:\n\n${data.responseText}`);
        });
    }

    /**
     * Call API to delete a device.
     */
    const deleteDevice = () => {
        const data = { device: dm.current.id };

        $.ajax({
            url: '/api/system/devices',
            type: 'DELETE',
            data: JSON.stringify(data),
            contentType: 'application/json;charset=UTF-8'
        }).done((/** @type {DeletedDeviceFromApi} */ data) => {
            console.log(`Device deleted successfully. Response:\n\n${JSON.stringify(data, null, '\t')}`);

            new Toast(`Device '${dm.current.name}' deleted.`).success();

            devices = devices.filter(d => d.id !== data.deleted_device);

            if (devices.length) {
                dm.current = devices[devices.length - 1];
                localStorage.setItem('lastDevice', dm.current.id);
            } else {
                dm.current = null;
                localStorage.removeItem('lastDevice');
            }

            _reloadDeviceBar(devices);

        }).fail((data) => {
            console.log(`Error while deleting device '${dm.current.name}'. Error:\n\n${data.responseText}`);
        });
    }

    /**
     * Serialize device settings to JSON.
     */
    const setLocalSettings = () => {
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

        const deviceSettings = {
            device: dm.current.id,
            settings: serializedDeviceForm
        };

        const settingsPromises = [
            $.ajax({
                url: '/api/settings/device',
                type: 'POST',
                data: JSON.stringify(deviceSettings),
                contentType: 'application/json;charset=UTF-8'
            }).done((data) => {
                console.log(`Device settings set successfully. Response:\n\n${JSON.stringify(data, null, '\t')}`);
                dm.current.name = data.settings.device_name;
                $('#selected_device_txt').text(data.settings.device_name);
            }).fail((data) => {
                console.log(`Error while setting '${dm.current.id}' settings. Error:\n\n${data.responseText}`);
            })
        ];

        // Serialize device output settings to JSON.
        Object.keys(outputTypes).forEach(outputType => {
            const serializedOutputForm = $(`#settingsForm .${outputType}`).serializeJSON({
                checkboxUncheckedValue: 'false'
            });

            const outputSettings = {
                device: dm.current.id,
                output_type_key: outputType,
                settings: serializedOutputForm
            };

            settingsPromises.push(
                $.ajax({
                    url: '/api/settings/device/output-type',
                    type: 'POST',
                    data: JSON.stringify(outputSettings),
                    contentType: 'application/json;charset=UTF-8'
                }).done((data) => {
                    console.log(`Device ${outputType} settings set successfully. Response:\n\n${JSON.stringify(data, null, '\t')}`);
                }).fail((data) => {
                    console.log(`Error while setting '${outputType}' settings. Error:\n\n${data.responseText}`);
                })
            );

        });

        Promise.all(settingsPromises).then(() => {
            console.log('All device settings saved.');
            new Toast(`Device '${dm.current.name}' saved.`).success();
        }).catch((data) => {
            new Toast(`Error while saving device '${dm.current.name}'.\n\n${JSON.parse(data.responseText).message}`).error();
        });

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
                dm.current = device;
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
     * Add group back to dropdown of global groups when group is removed from device.
     * @param {string} groupId
     */
    const _addGroupOption = (groupId) => {
        $(`#device_group_dropdown option[tag-id='${groupId}']`).show();
    }

    /**
     * Remove group from dropdown of global groups when group is added to device.
     * @param {JQuery} groupItem Dropdown item as a jQuery object.
     */
    const _removeGroupOption = (groupItem) => {
        groupItem.hide();
        groupItem.parent().get(0).selectedIndex = 0;  // Keep dropdown at 'Select a group' option.
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

    $('#create1_btn, #create2_btn').on('click', () => {
        createDevice();
    });

    $('#save_btn').on('click', () => {
        setLocalSettings();
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

    // Show/hide "Device Groups" tag section on tag input change.
    $('.tagin').on('change', () => {
        if (!tagin.getTags().length) {
            $('#device_group_pills').addClass('d-none');
            return;
        }
        $('#device_group_pills').removeClass('d-none');
    });

    // Add new group pill on dropdown option click.
    $('#device_group_dropdown').on('change', e => {
        const dropdownItem = $(e.currentTarget.selectedOptions[0]);
        _removeGroupOption(dropdownItem);

        const tagId = dropdownItem.attr('tag-id');
        tagin.addTag(dropdownItem.val(), tagId);
    });

    // Add group to dropdown on 'x' click.
    $('.tagin-wrapper').on('click', e => {
        if (e.target.closest('.tagin-tag-remove')) {
            const groupId = $(e.target).parent().attr('tag-id');
            _addGroupOption(groupId);
        }
    });

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
$('#LED_Strip_TOOLTIP').attr('data-original-title', 'The LED Strip type. Check if the RGB channels are mapped correctly.<br><br>Default setting: ws281x_rgb');
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

/**
 * @typedef {object} NewDeviceFromApi
 * @property {string} device_id
 */

/**
 * @typedef {object} DeletedDeviceFromApi
 * @property {string} deleted_device
 */
