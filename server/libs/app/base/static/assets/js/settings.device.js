import Device from "./classes/Device.js";

let output_types = {};
let devices = [];
let currentDevice;

function createToast(message, isSuccess = true) {
    let textClass, title, icon;
    if (isSuccess) {
        textClass = 'text-success';
        icon = 'icon-check';
        title = 'Success';
    } else {
        textClass = 'text-danger';
        icon = 'icon-alert-triangle';
        title = 'Error';
    }

    let customToast = `
        <div class="toast" style="min-width: 250px;" role="alert" aria-live="assertive" aria-atomic="true" data-delay="5000">
            <div class="toast-header">
                <strong class="mr-auto ` + textClass + `"><i class="feather ` + icon + `"></i> ` + title + `</strong>
                <small class="text-muted">`+ new Date().toLocaleTimeString('en-GB') + `</small>
                <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="Close">
                    <span aria-hidden="true" class="feather icon-x"></span>
                </button>
            </div>
            <div class="toast-body">
                ` + message + `
            </div>
        </div>
    `;

    return customToast;
}

function refreshDeviceConfig(output_types, currentDevice) {
    if (!currentDevice) return;
    // fetch Device Config data from Server and update the Form
    const device_config_input = $(".device_setting_input").map(function () { return this.id }).toArray()
        .map(id => currentDevice.getSetting(id));
    const device_config_output = Object.keys(output_types).flatMap(output_type_key => {
        return $("." + output_type_key).map(function () { return this.id }).toArray()
            .map(key => currentDevice.getOutputSetting(key, output_type_key))
    });
    Promise.all(
        device_config_input
            .concat(device_config_output)
    )
        .then((response) => {
            // response array contains ALL current device config objects
            response.forEach(data => {
                const setting_key = data["setting_key"];
                const setting_value = data["setting_value"];
                $("#" + setting_key).trigger('change');

                if ($(`#${setting_key}`).attr('type') == 'checkbox') {
                    $(`#${setting_key}`).prop('checked', setting_value);
                } else {
                    $(`#${setting_key}`).val(setting_value);
                }
                $(`#${setting_key}`).trigger('change');

                // Set initial brightness slider value
                $(`span[for='${setting_key}']`).text(setting_value)
            })
        });
}

// Init and load all settings
$(document).ready(function () {
    // Preload
    Promise.all([
        // get Output Types
        $.ajax("/GetOutputTypes").done((data) => {
            output_types = data;
            $('.output_type').each(function () {
                Object.keys(data).forEach(output_type_key => {
                    const option = new Option(data[output_type_key], output_type_key);
                    $(this).append(option);
                });
            });
        }),
        // get LED Strips
        $.ajax("/GetLEDStrips").done((data) => {
            $('.led_strips').each(function () {
                for (let key in data) {
                    $(this).append(new Option(data[key], key));
                }
            });
        }),
    ]).then(response => {
        // all requests finished successfully
        $.ajax("/GetDevices").done((data) => {
            // parse data into device Objects
            Object.keys(data).forEach(device_key => {
                devices.push(new Device(device_key, data[device_key]));
            });

            // Restore last selected device on reload
            let lastDevice = devices.find(device => device.id === localStorage.getItem("lastDevice"));
            if (lastDevice instanceof Device) {
                currentDevice = lastDevice;
            } else {
                // Fallback to all_devices
                currentDevice = devices.length > 0 ? devices[0] : undefined;
            }

            refreshDeviceConfig(output_types, currentDevice)

            // Build Device Tab
            devices.forEach((device, index) => {
                // todo: do it server side
                const link = device.getPill(currentDevice.id, index);
                link.addEventListener('click', () => {
                    currentDevice = device;
                    localStorage.setItem('lastDevice', device.id);
                    $("#selected_device_txt").text(device.name);
                    refreshDeviceConfig(output_types, currentDevice)
                });

                const li = document.createElement("li");
                li.className = "nav-item device_item";
                li.appendChild(link)

                document.getElementById("deviceTabID").appendChild(li);
            });

            $('#device_count').text(devices.length);

            if (devices.length > 0) {
                $("#deviceFound").removeClass('d-none');
                $("#noDeviceFound").addClass('d-none');
            } else {
                $("#deviceFound").addClass('d-none');
                $("#noDeviceFound").removeClass('d-none');
                return;
            }

            $("#selected_device_txt").text(currentDevice.name);

        })
    }).catch((response) => {
        if (devices.length === 0) {
            return;
        }
        console.warn(response);
        // all requests finished but one or more failed
        $("#alerts").append(`
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>(`+ new Date().toLocaleTimeString() + `) Error: </strong>${response.responseText}
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
            <span aria-hidden="true">&times;</span>
            </button>
            </div>`);
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
            case "number":
                setting_value = parseFloat(element.val());
                break;
            default:
                setting_value = element.val();
        }
        settings_device[setting_key] = setting_value;
    });
    const data = { "device": currentDevice.id, "settings": settings_device };

    const saveProgress = [
        $.ajax({
            url: "/SetDeviceSetting",
            type: "POST",
            data: JSON.stringify(data, null, '\t'),
            contentType: 'application/json;charset=UTF-8'
        }).done((data) => {
            console.log("Device settings set successfully. Response:\n\n" + JSON.stringify(data, null, '\t'));

            // Update device name in device dropdown
            // Todo: Update device name inside pill too
            currentDevice.name = data.settings.DEVICE_NAME
            $("#selected_device_txt").text(currentDevice.name);
            $("#selected_device_txt").text(currentDevice.name);

            let customToast = createToast('Device "' + currentDevice.name + '" saved.')
            $(".toast_block").append(customToast)
            $('.toast').toast('show')
            $('.toast').on('hidden.bs.toast', function () {
                $(this).remove()
            })

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
                url: "/SetOutputTypeDeviceSetting",
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
        // todo: show toast alert
        console.warn(response);
    });

}

const createDevice = function () {
    $.ajax({
        url: "/CreateNewDevice",
        type: "POST",
        contentType: 'application/json;charset=UTF-8'
    }).done(data => {
        console.log("New device created successfully. Response:\n\n" + JSON.stringify(data, null, '\t'));
        let newDeviceIndex = data["index"];
        // location.reload();
        $.ajax("/GetDevices").done((data) => {
            devices = [];
            // parse data into device Objects
            Object.keys(data).forEach(device_key => {
                devices.push(new Device(device_key, data[device_key]));
            });

            // Select newly created Device by its index
            currentDevice = devices[newDeviceIndex]
            refreshDeviceConfig(output_types, currentDevice);

            // Remove every pill in the navigation and recreate
            const tabs = document.getElementById("deviceTabID");
            tabs.innerHTML = "";

            // Build Device Tab
            devices.forEach((device, index) => {
                // todo: do it server side
                const link = device.getPill(currentDevice.id, index);
                link.addEventListener('click', () => {
                    currentDevice = device;
                    localStorage.setItem('lastDevice', device.id);
                    $("#selected_device_txt").text(device.name);
                    refreshDeviceConfig(output_types, currentDevice)
                });

                const li = document.createElement("li");
                li.className = "nav-item device_item";
                li.appendChild(link)
                tabs.appendChild(li);
            });

            $('#device_count').text(devices.length);
            $("#selected_device_txt").text(currentDevice.name);
            $("#deviceFound").removeClass('d-none');
            $("#noDeviceFound").addClass('d-none');

            let customToast = createToast('Device "' + currentDevice.name + '" created.')
            $(".toast_block").append(customToast)
            $('.toast').toast('show')
            $('.toast').on('hidden.bs.toast', function () {
                $(this).remove()
            })

        })

    }).fail(data => {
        console.log("Error while creating new device. Error: " + data.responseText);
    });
}
document.getElementById("save_btn").addEventListener("click", function (e) {
    SetLocalSettings();
});

document.getElementById("create1_btn").addEventListener("click", createDevice);

document.getElementById("create2_btn").addEventListener("click", createDevice);

document.getElementById("delete_btn").addEventListener("click", function (e) {
    $('#modal_device_name').text(currentDevice.name)
    $('#modal_delete_device').modal('show')
});

document.getElementById("delete_btn_modal").addEventListener("click", function (e) {
    $('#modal_delete_device').modal('hide')
    $.ajax({
        url: "/DeleteDevice",
        type: "POST",
        data: JSON.stringify({ "device": currentDevice.id }, null, '\t'),
        contentType: 'application/json;charset=UTF-8'
    }).done(data => {
        console.log("Device deleted successfully. Response:\n\n" + JSON.stringify(data, null, '\t'));
        location.reload();
    }).fail(data => {
        console.log("Error while deleting device. Error: " + data.responseText);
    });

});
