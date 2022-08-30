import { Device, tagin } from "./classes/Device.js";
import Toast from "./classes/Toast.js";


// Init and load all settings.
$(() => {
    $("#settings_list").slideDown();
    $(".tagin-input").prop('disabled', true);

    let outputTypes;
    /**
     * @type {Array.<Device>}
     */
    let devices = jinja_devices.map(d => { return new Device(d) });
    /**
     * @type {Device}
     */
    let currentDevice = devices.find(d => d.id === localStorage.getItem("lastDevice")) || devices[0];

    // Preload dropdown values.
    Promise.all([

        $.ajax("/api/resources/output-types").done((response) => {
            outputTypes = response;
            Object.entries(response).forEach(([key, value]) => {
                $('.output_type').append(`<option value="${key}">${value}</option>`);
            });
        }),

        $.ajax("/api/resources/led-strips").done((response) => {
            Object.entries(response).forEach(([key, value]) => {
                $('.led_strips').append(`<option value="${key}">${value}</option>`);
            });
        })

    ]).then(() => {
        if (jinja_devices.length > 0) {
            $("#deviceFound").removeClass('d-none');
            $("#noDeviceFound").addClass('d-none');
        } else {
            $("#deviceFound, #selected_device_label").addClass('d-none');
            $("#noDeviceFound").removeClass('d-none');
            return;
        }

        // Get device id from url parameters.
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('id')) {
            const passedId = urlParams.get('id');
            const selectedDeviceFromUrl = devices.find(device => device.id === passedId);
            if (selectedDeviceFromUrl !== undefined) {
                currentDevice = selectedDeviceFromUrl;
            }
        }

        localStorage.setItem('lastDevice', currentDevice.id);
        $(`a[data-device_id=${currentDevice.id}`).addClass("active");
        $("#selected_device_txt").text(currentDevice.name);
        currentDevice.refreshConfig();

        // Add behavior to Device Tab.
        devices.forEach(device => {
            $(device.link).on('click', () => {
                currentDevice = device;
                device.refreshConfig();
            });
        });

    }).catch((response) => {
        // All requests finished but one or more failed.
        new Toast(JSON.stringify(response, null, '\t')).error();
    });

    $("#save_btn").on("click", () => {
        setLocalSettings();
    });

    $("#create1_btn, #create2_btn").on("click", () => {
        createDevice();
    });

    $("#delete_btn").on("click", () => {
        $('#modal_device_name').text(currentDevice.name);
        $('#modal_delete_device').modal('show');
    });

    $("#delete_btn_modal").on("click", () => {
        $('#modal_delete_device').modal('hide');
        deleteDevice();
    })

    // Do not allow special symbols except for _-. in device name.
    $("#device_name").on("input", e => {
        let position = e.currentTarget.selectionStart,
            regex = /[!$%^&*()+|~=`{}\[\]:";'<>?,\/]/gi,
            textVal = e.currentTarget.value;
        if (regex.test(textVal)) {
            $(e.currentTarget).val(textVal.replace(regex, ''));
            position--;
        }
        e.currentTarget.setSelectionRange(position, position);
    });

    // Add new group pill on dropdown option click.
    $("#device_group_dropdown").on("change", () => {
        const deviceGroup = $("#device_group_dropdown").val();
        const tagId = removeGroupOption(deviceGroup);
        tagin.addTag(deviceGroup, tagId);
    });

    $(".tagin").on("change", () => {
        if (tagin.getTags().length === 0) {
            $('#device_group_pills').addClass("d-none");
        } else {
            $('#device_group_pills').removeClass("d-none");
        }
    });

    // Add group to dropdown on "x" click.
    $(".tagin-wrapper").on("click", e => {
        if (e.target.closest(".tagin-tag-remove")) {
            const groupElement = e.target.closest(".tagin-tag-remove").parentElement;
            const group = groupElement.innerText;
            const groupId = groupElement.getAttribute("tag-id");
            addGroupOption(group, groupId);
        }
    });

    // Set LED strip brightness slider badge.
    $("input[type=range]").on("input", e => {
        $(`span[for='${$(e.currentTarget).attr('id')}']`).text(e.currentTarget.value);
    });

    // Hide unused output settings.
    $("#output_type").on("change", () => {
        if ($("#output_type").val() === "output_raspi") {
            $("#raspberrypi").removeClass("d-none");
            $("#udp").addClass("d-none");
        } else {
            $("#udp").removeClass("d-none");
            $("#raspberrypi").addClass("d-none");
        }
    });

    // Limit "led_mid" input to be between 0 and "led_count".
    $("#led_mid").on("input", () => {
        const led_mid = $("#led_mid").val();
        const led_count = $("#led_count").val();
        if (parseInt(led_mid) >= parseInt(led_count)) {
            $("#led_mid").val(parseInt(led_count) - 1);
        } else if (led_mid.startsWith("0")) {
            $("#led_mid").val(led_mid.substring(1));
        }
    });

    /**
     * Call API to create new default device.
     */
    const createDevice = () => {
        $.ajax({
            url: "/api/system/devices",
            type: "POST",
            contentType: 'application/json;charset=UTF-8'
        }).done(data => {
            console.log("New device created successfully. Response:\n\n" + JSON.stringify(data, null, '\t'));
            const newDeviceId = data["device_id"];

            $.ajax("/api/system/devices").done((data) => {
                // Parse data into device Objects.
                devices = data.map(d => { return new Device(d) });
                // Select newly created Device by its device ID.
                currentDevice = devices.find(d => d.id === newDeviceId);
                currentDevice.refreshConfig();
                reloadDeviceTab();
                localStorage.setItem('lastDevice', currentDevice.id);

                $("#deviceFound, #selected_device_label").removeClass('d-none');
                $("#noDeviceFound").addClass('d-none');

                new Toast(`Device "${currentDevice.name}" created.`).success();
            });
        }).fail(data => {
            console.log("Error while creating new device. Error: " + data.responseText);
        });
    }

    /**
     * Call API to delete a device.
     */
    const deleteDevice = () => {
        $.ajax({
            url: "/api/system/devices",
            type: "DELETE",
            data: JSON.stringify({ "device": currentDevice.id }, null, '\t'),
            contentType: 'application/json;charset=UTF-8'
        }).done(data => {
            console.log("Device deleted successfully. Response:\n\n" + JSON.stringify(data, null, '\t'));

            new Toast(`Device "${currentDevice.name}" deleted.`).success();
            devices = devices.filter(d => d.id !== data.device);

            if (devices.length) {
                currentDevice = devices[[devices.length - 1]];
                currentDevice.refreshConfig();
                localStorage.setItem('lastDevice', currentDevice.id);
            } else {
                $("#deviceFound, #selected_device_label").addClass('d-none');
                $("#noDeviceFound").removeClass('d-none');
                localStorage.removeItem('lastDevice');
            }
            reloadDeviceTab();
        }).fail(data => {
            console.log(`Error while deleting device "${currentDevice.name}". Error: ${data.responseText}`);
        });
    }

    /**
     * Serialize device settings to JSON.
     */
    const setLocalSettings = () => {
        // Do not save device settings if device name already exists.
        const nameExists = devices.some(d => $("#device_name").val() === d.name && currentDevice.id !== d.id);
        if (nameExists) {
            new Toast(`Device with the name "${$("#device_name").val()}" already exists.`).error();
            return;
        }

        const serializedDeviceForm = $('#settingsForm .device_setting_input').serializeJSON({
            checkboxUncheckedValue: "false",
            customTypes: {
                name: (value) => { return value.trim() },
                ledcount: (value) => {
                    // https://github.com/rpi-ws281x/rpi-ws281x-python/issues/70
                    if (isNaN(value) || value < 7) {
                        return 7
                    }
                    return parseInt(value);
                },
                tags: () => { return tagin.getTagObjects(); }
            }
        });

        const deviceSettings = {
            "device": currentDevice.id,
            "settings": serializedDeviceForm
        };

        const saveProgress = [
            $.ajax({
                url: "/api/settings/device",
                type: "POST",
                data: JSON.stringify(deviceSettings, null, '\t'),
                contentType: 'application/json;charset=UTF-8'
            }).done((data) => {
                console.log("Device settings set successfully. Response:\n\n" + JSON.stringify(data, null, '\t'));
                currentDevice.name = data.settings.device_name;
                $("#selected_device_txt").text(currentDevice.name);

                new Toast(`Device "${currentDevice.name}" saved.`).success();

            }).fail((data) => {
                console.log("Error while setting device settings. Error: " + data);
            })
        ];

        // Serialize device output settings to JSON.
        Object.keys(outputTypes).forEach(outputType => {
            const serializedOutputForm = $(`#settingsForm .${outputType}`).serializeJSON({
                checkboxUncheckedValue: "false"
            });

            const outputSettings = {
                "device": currentDevice.id,
                "output_type_key": outputType,
                "settings": serializedOutputForm
            };

            saveProgress.push(
                $.ajax({
                    url: "/api/settings/device/output-type",
                    type: "POST",
                    data: JSON.stringify(outputSettings, null, '\t'),
                    contentType: 'application/json;charset=UTF-8'
                }).done(data => {
                    console.log(`Device ${outputType} settings set successfully. Response:\n\n` + JSON.stringify(data, null, '\t'));
                }).fail(data => {
                    console.log("Error while setting device settings. Error: " + data);
                })
            );

        });

        Promise.all(saveProgress).then(() => {
            console.log("all saved");
        }).catch((response) => {
            new Toast(`Error while saving device "${currentDevice.name}". Error: ` + JSON.stringify(response, null, '\t')).error();
        });

    }

    /**
     * Update pills in device bar with new data.
     */
    const reloadDeviceTab = () => {
        // Remove every pill in the navigation and recreate.
        const tabs = document.getElementById("deviceTabID");
        tabs.innerHTML = "";

        // Build Device Tab.
        devices.forEach(device => {
            device.getPill(currentDevice.id);

            $(device.link).on('click', () => {
                currentDevice = device;
                $("#selected_device_txt").text(device.name);
                device.refreshConfig();
            });

            const li = document.createElement("li");
            li.className = "nav-item device_item";
            li.appendChild(device.link);
            tabs.appendChild(li);
        });

        $('#device_count').text(devices.length);
        $("#selected_device_txt").text(currentDevice.name);
    }

    /**
     * Add group back to dropdown of global groups when group is removed from device.
     * @param {string} group
     * @param {string} groupId
     */
    const addGroupOption = (group, groupId) => {
        $("#device_group_dropdown").append(`<option tag-id="${groupId}" value="${group}">${group}</option>`);
    }

    /**
     * Remove group from dropdown of global groups when group is added to device.
     * @param {string} group
     * @return {string} `tagId` of the group
     */
    const removeGroupOption = (group) => {
        let groupOption = $(`#device_group_dropdown option[value="${group}"]`);
        groupOption.remove();
        $("#device_group_dropdown")[0].selectedIndex = 0;
        return groupOption.attr("tag-id");
    }

});


// Tooltip descriptions for device settings
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
