import Device from "./classes/Device.js";
import EffectManager from "./classes/EffectManager.js";

// Global Variables
const effectManager = new EffectManager();

// Start with Fake Device
const devices = [new Device("all_devices", "All Devices")];
let currentDevice = devices[0];

// Init and load all settings
$(document).ready(function () {

    $.ajax("/GetDevices").done((data) => {
        // data = { device_0: "devicename1", device_1: "devicename2" }
        // todo: return anon Objects from Endpoint

        if(!Object.keys(data).length){
            $("#alerts").append(`
            <div class="alert alert-info alert-dismissible fade show" role="alert">
            <strong>No Devices found</strong><hr><a href="#" class='btn btn-primary'>Create a new device</a>
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
              <span aria-hidden="true">&times;</span>
            </button>
            </div>`);
        }

        // parse response into device Objects
        Object.keys(data).forEach(device_key => {
            devices.push(new Device(device_key, data[device_key]));
        });

        // Subtract the fake Device
        $('#device_count').text(devices.length-1);

        // Restore last selected device on reload
        let lastDevice = devices.find(device => device.id === localStorage.getItem("lastDevice"));
        if(lastDevice instanceof Device) {
            currentDevice = lastDevice;
        } else {
            // Fallback to all_devices
            currentDevice = devices[0];
        }

        effectManager.currentDevice = currentDevice;

        // Async function
        currentDevice.getActiveEffect();

        // Build Device Tab
        devices.forEach((device, index) => {
            // todo: do it server side
            const active = currentDevice.id === device.id ? " active" : "";
            const link = document.createElement("a");
            link.classList = "nav-link"+active;
            link.innerHTML = device.name;
            link.href = `#pills-${index}`;
            link.role = "tab";
            link.setAttribute("data-toggle", "pill")
            link.setAttribute("aria-controls", `pills-${index}`)
            link.setAttribute("aria-selected", "false")
            link.addEventListener('click', () => {
                currentDevice = device;
                localStorage.setItem('lastDevice', device.id);
                effectManager.currentDevice = currentDevice;
                // Async function
                device.getActiveEffect();
            });

            const li = document.createElement("li");
            li.className = "nav-item device_item";
            li.appendChild(link)

            document.getElementById("deviceTabID").appendChild(li);
        });
     });
});