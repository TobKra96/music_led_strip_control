import Device from "./classes/Device.js";
import Toast from "./classes/Toast.js";

let output_types = {};
let devices = jinja_devices.map(d => { return new Device(d) });
let currentDevice = devices.find(d => d.id === localStorage.getItem("lastDevice"));
// Select first device if previously "All Devices" selected or localStorage is clear
currentDevice = currentDevice ? currentDevice : devices[0];
if (currentDevice) {
    $(`a[data-device_id=${currentDevice.id}`).removeClass("active");
}

// Get device id from url parameters
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.has('id')) {
    let passedId = urlParams.get('id');
    let selectedDeviceFromUrl = devices.find(device => device.id === passedId);
    if (selectedDeviceFromUrl !== undefined) {
        currentDevice = selectedDeviceFromUrl;
    }
}

if (currentDevice) {
    localStorage.setItem('lastDevice', currentDevice.id);
    $(`a[data-device_id=${currentDevice.id}`).addClass("active");
    $("#selected_device_txt").text(currentDevice.name);
}


// Init and load all settings
$(document).ready(function () {
    $("#settings_list").slideDown();
    // Preload
    Promise.all([
        // get Output Types
        $.ajax("/api/resources/output-types").done((data) => {
            output_types = data;
            $('.output_type').each(function () {
                Object.keys(data).forEach(output_type_key => {
                    const option = new Option(data[output_type_key], output_type_key);
                    $(this).append(option);
                });
            });
        }),
        // get LED Strips
        $.ajax("/api/resources/led-strips").done((data) => {
            $('.led_strips').each(function () {
                for (let key in data) {
                    $(this).append(new Option(data[key], key));
                }
            });
        }),
    ]).then(response => {
        if (devices.length > 0) {
            $("#deviceFound").removeClass('d-none');
            $("#noDeviceFound").addClass('d-none');
            $("#selected_device_label").removeClass('d-none');
        } else {
            $("#deviceFound").addClass('d-none');
            $("#noDeviceFound").removeClass('d-none');
            $("#selected_device_label").addClass('d-none');
            return;
        }

        currentDevice.refreshConfig(output_types);
        // Add behavior to Device Tab
        devices.forEach(device => {
            device.link.addEventListener('click', () => {
                currentDevice = device;
                device.refreshConfig(output_types);
            });
        });

    }).catch((response) => {
        if (devices.length === 0) {
            return;
        }
        // all requests finished but one or more failed
        new Toast(JSON.stringify(response, null, '\t')).error();
    });

});

// Save Functions   -----------------------------------------------------------

function SetLocalSettings() {
    let settings_device = {};
    $(".device_setting_input").each((i, v) => {
        const setting_key = v.id;
        let setting_value = "";

        const element = $(`#${setting_key}.device_setting_input`);
        switch (element.attr("type")) {
            case "checkbox":
                setting_value = element.is(':checked');
                break;
            case "range":
            case "number":
                if (!element.val()) {
                    setting_value = 1;
                } else if (setting_key == "led_count" && element.val() < 7) {
                    // https://github.com/rpi-ws281x/rpi-ws281x-python/issues/70
                    setting_value = 7;
                } else {
                    setting_value = parseFloat(element.val());
                }
                break;
            case "option":
                let groups = [];
                element.children("span").each(function () {
                    groups.push($(this).attr('value'));
                });
                setting_value = groups;
                break;
            default:
                setting_value = element.val().trim();
                element.val(setting_value);
        }
        settings_device[setting_key] = setting_value;
    });
    const data = { "device": currentDevice.id, "settings": settings_device };

    const saveProgress = [
        $.ajax({
            url: "/api/settings/device",
            type: "POST",
            data: JSON.stringify(data, null, '\t'),
            contentType: 'application/json;charset=UTF-8'
        }).done((data) => {
            console.log("Device settings set successfully. Response:\n\n" + JSON.stringify(data, null, '\t'));
            currentDevice.name = data.settings.device_name;
            $("#selected_device_txt").text(data.settings.device_name);

            new Toast(`Device "${currentDevice.name}" saved.`).success();

        }).fail((data) => {
            console.log("Error while setting device settings. Error: " + data);
        })
    ];

    Object.keys(output_types).forEach(output_type_key => {
        const all_output_type_setting_keys = $("." + output_type_key).map(function () { return this.id }).toArray();
        let settings_output_type = {};

        Object.keys(all_output_type_setting_keys).forEach((setting_id) => {
            const setting_key = all_output_type_setting_keys[setting_id];
            let setting_value = "";

            const element = $(`#${setting_key}.${output_type_key}`);
            switch (element.attr("type")) {
                case "checkbox":
                    setting_value = element.is(':checked');
                    break;
                case "number":
                    setting_value = parseFloat(element.val());
                    break;
                default:
                    setting_value = element.val();
            }
            settings_output_type[setting_key] = setting_value;
        });

        const data2 = { "device": currentDevice.id, "output_type_key": output_type_key, "settings": settings_output_type };
        saveProgress.push(
            $.ajax({
                url: "/api/settings/device/output-type",
                type: "POST",
                data: JSON.stringify(data2, null, '\t'),
                contentType: 'application/json;charset=UTF-8'
            }).done(data => {
                console.log("Device settings set successfully. Response:\n\n" + JSON.stringify(data, null, '\t'));
            }).fail(data => {
                console.log("Error while setting device settings. Error: " + data);
            })
        );

    });

    Promise.all(saveProgress).then(response => {
        console.log("all saved", response);
    }).catch((response) => {
        new Toast(`Error while saving device "${currentDevice.name}". Error: ` + JSON.stringify(response, null, '\t')).error();
    });

}

const createDevice = function () {
    $.ajax({
        url: "/api/system/devices",
        type: "POST",
        contentType: 'application/json;charset=UTF-8'
    }).done(data => {
        console.log("New device created successfully. Response:\n\n" + JSON.stringify(data, null, '\t'));
        let newDeviceIndex = data["index"];
        // location.reload();
        $.ajax("/api/system/devices").done((data) => {
            const newDeviceId = data.find(d => d.id === `device_${newDeviceIndex}`);
            localStorage.setItem('lastDevice', newDeviceId.id);
            // parse data into device Objects
            devices = data.map(d => { return new Device(d) });

            // Select newly created Device by its index
            currentDevice = devices.find(d => d.id === `device_${newDeviceIndex}`);
            localStorage.setItem('lastDevice', currentDevice.id);

            // $(`a[data-device_id=${currentDevice.id}`).addClass("active");
            currentDevice.refreshConfig(output_types);

            reloadDeviceTab(devices);

            $("#selected_device_label").removeClass('d-none');
            $("#deviceFound").removeClass('d-none');
            $("#noDeviceFound").addClass('d-none');

            new Toast(`Device "${currentDevice.name}" created.`).success();

        })

    }).fail(data => {
        console.log("Error while creating new device. Error: " + data.responseText);
    });
}

// Do not allow special symbols except for [-_.] in device name
$('#device_name').on('input', function () {
    let position = this.selectionStart,
        regex = /[!$%^&*()+|~=`{}\[\]:";'<>?,\/]/gi,
        textVal = $(this).val();
    if (regex.test(textVal)) {
        $(this).val(textVal.replace(regex, ''));
        position--;
    }
    this.setSelectionRange(position, position);
});

// Add new group pill on dropdown option click
$("#device_group_dropdown").on("change", function () {
    let deviceGroup = $("#device_group_dropdown").val();
    let exists = 0 != $(`#device_groups span[value="${deviceGroup}"]`).length;
    if (deviceGroup && !exists) {
        addGroupPill(deviceGroup);
        removeGroupOption(deviceGroup);
    }
});

// Remove group pill on "x" click
$("#device_groups").on("click", ".badge > span", function () {
    let group = $(this).parent().attr('value');
    addGroupOption(group);
    removeGroupPill(group);
});

$("#device_groups").on("mouseover mouseleave", ".badge > span", function (event) {
    event.preventDefault();
    $(this).parent().toggleClass("badge-primary");
    $(this).parent().toggleClass("badge-danger");
});

$("#save_btn").on("click", function () {
    // Do not save device settings if device name already exists
    let deviceNameExists = devices.some( device => $("#device_name").val() === device._name && currentDevice.id !== device.id );
    if (deviceNameExists) {
        new Toast(`Device "${$("#device_name").val()}" already exists.`).warning();
    } else {
        SetLocalSettings();
    }
});

$("#create1_btn, #create2_btn").on("click", function () {
    createDevice();
});

$("#delete_btn").on("click", function () {
    $('#modal_device_name').text(currentDevice.name);
    $('#modal_delete_device').modal('show');
})

$("#delete_btn_modal").on("click", function () {
    $('#modal_delete_device').modal('hide');
    $.ajax({
        url: "/api/system/devices",
        type: "DELETE",
        data: JSON.stringify({ "device": currentDevice.id }, null, '\t'),
        contentType: 'application/json;charset=UTF-8'
    }).done(data => {
        localStorage.removeItem('lastDevice');
        console.log("Device deleted successfully. Response:\n\n" + JSON.stringify(data, null, '\t'));

        new Toast(`Device "${currentDevice.name}" deleted.`).success();

        devices = $.grep(devices, function (e) {
            return e.id != data.device;
        });

        if (devices.length) {
            currentDevice = devices[[devices.length - 1]];
            localStorage.setItem('lastDevice', currentDevice.id);
            currentDevice.refreshConfig(output_types);
        } else {
            $("#deviceFound").addClass('d-none');
            $("#noDeviceFound").removeClass('d-none');
            $("#selected_device_label").addClass('d-none');
        }

        reloadDeviceTab(devices);

    }).fail(data => {
        new Toast(`Error while deleting device "${currentDevice.name}". Error: ${data.responseText}`).error();
    });
})

function reloadDeviceTab(devices) {
    // Remove every pill in the navigation and recreate
    const tabs = document.getElementById("deviceTabID");
    // tabs.innerHTML = `
    //     <li class="nav-item">
    //         <a class="nav-link">
    //             <span class="badge badge-secondary" id="">Devices</span>
    //         </a>
    //     </li>
    // `;
    tabs.innerHTML = "";

    // Build Device Tab
    devices.forEach(device => {
        device.getPill(currentDevice.id);

        device.link.addEventListener('click', () => {
            currentDevice = device;
            $("#selected_device_txt").text(currentDevice.name);
            device.refreshConfig(output_types);
        });

        const li = document.createElement("li");
        li.className = "nav-item device_item";
        li.appendChild(device.link);
        tabs.appendChild(li);
    });

    $('#device_count').text(devices.length);
    $("#selected_device_txt").text(currentDevice.name);
}

function addGroupPill(group) {
    const pill = `<span class="badge badge-primary badge-pill" value="${group}">${group} <span class="feather icon-x"></span></span> `;
    $("#device_groups").append(pill);

    if ($('#device_groups').children().length > 0) {
        $('#device_group_label').removeClass("d-none");
    }
}

function removeGroupPill(group) {
    let groupPill = $(`#device_groups span[value="${group}"]`);
    groupPill.remove();

    if ($('#device_groups').children().length === 0) {
        $('#device_group_label').addClass("d-none");
    }
}

function addGroupOption(group) {
    const option = new Option(group, group);
    $("#device_group_dropdown").append(option);
}

function removeGroupOption(group) {
    let groupOption = $(`#device_group_dropdown option[value="${group}"]`);
    groupOption.remove();
    $("#device_group_dropdown")[0].selectedIndex = 0;
}

// Set LED strip brightness slider badge
$('input[type=range]').on('input', function () {
    $("span[for='" + $(this).attr('id') + "']").text(this.value);
});

// Hide unused output settings
$('#output_type').on('change', () => {
    if ($('#output_type').val() == 'output_raspi') {
        $('#raspberrypi').removeClass('d-none');
        $('#udp').addClass('d-none');
    } else {
        $('#udp').removeClass('d-none');
        $('#raspberrypi').addClass('d-none');
    }
});

// Limit led_mid input to be between 0 and led_count
$('#led_mid').on('input', () => {
    let led_mid = $('#led_mid').val()
    let led_count = $('#led_count').val()
    if (parseInt(led_mid) >= parseInt(led_count)) {
        $('#led_mid').val(parseInt(led_count) - 1)
    } else if (led_mid.startsWith('0')) {
        $('#led_mid').val(led_mid.substring(1))
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
