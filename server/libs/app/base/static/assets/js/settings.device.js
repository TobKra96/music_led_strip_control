import Device from "./classes/Device.js";
import Toast from "./classes/Toast.js";

let output_types = {};
let devices = jinja_devices.map(d => { return new Device(d) });
// select first device if previously "All Devcies" selected
// could this be done better?
let currentDevice = devices.find(d => d.id === localStorage.getItem("lastDevice") );
currentDevice = currentDevice ? currentDevice : devices[devices.length-1];
localStorage.setItem('lastDevice', currentDevice.id);
$(`a[data-device_id=${currentDevice.id}`).addClass("active");
$("#selected_device_txt").text(currentDevice.name);
console.log("curr dev", currentDevice);

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
        currentDevice.refreshConfig(output_types);

        // Add behavior to Device Tab
        devices.forEach(device => {
            device.link.addEventListener('click', () => {
                currentDevice = device;
                device.refreshConfig(output_types);
            });
        });

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
        new Toast(`Error while saving device "${currentDevice.name}". Error: ` + JSON.stringify(response, null, '\t')).error();
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
        $.ajax("/GetDevices2").done((data) => {

            console.warn(data);
            const newDeviceId = data.find(d => d.id === `device_${newDeviceIndex}` );
            localStorage.setItem('lastDevice', newDeviceId.id);
            // parse data into device Objects
            devices = data.map(d => { return new Device(d) });

            // Select newly created Device by its index
            currentDevice = devices.find(d => d.id === `device_${newDeviceIndex}` );
            localStorage.setItem('lastDevice', currentDevice.id);

            // $(`a[data-device_id=${currentDevice.id}`).addClass("active");
            currentDevice.refreshConfig(output_types);

            // Remove every pill in the navigation and recreate
            const tabs = document.getElementById("deviceTabID");
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
            $("#selected_device_label").removeClass('d-none');
            $("#selected_device_txt").text(currentDevice.name);
            $("#deviceFound").removeClass('d-none');
            $("#noDeviceFound").addClass('d-none');

            new Toast(`Device "${currentDevice.name}" created.`).success();

        })

    }).fail(data => {
        console.log("Error while creating new device. Error: " + data.responseText);
    });
}

$("#save_btn").on("click", function () {
    SetLocalSettings();
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
        url: "/DeleteDevice",
        type: "POST",
        data: JSON.stringify({ "device": currentDevice.id }, null, '\t'),
        contentType: 'application/json;charset=UTF-8'
    }).done(data => {
        localStorage.removeItem('lastDevice');
        console.log("Device deleted successfully. Response:\n\n" + JSON.stringify(data, null, '\t'));
        // Todo: Delete device without reloading
        // Todo: Add toast on success
        location.reload();
    }).fail(data => {
        new Toast(`Error while deleting device "${currentDevice.name}". Error: ${data.responseText}`).error();
    });
})
