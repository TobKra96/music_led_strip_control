import Device from "./classes/Device.js";
import Toast from "./classes/Toast.js";


$(function () {

    if (!jinja_devices.length) {
        new Toast('No device found. Create a new device in "Device Settings".').info();
        return;
    }

    // Create Base Device ("all_devices").
    const baseDevice = new Device({ groups: [], id: "all_devices", name: "All Devices" })

    // Create Devices from Jinja output.
    const devices = [baseDevice].concat(jinja_devices.map(d => { return new Device(d) }));

    devices.forEach(device => {
        device.link.addEventListener('click', () => {
            // Async function
            device.getActiveEffect();
        });
    });

});
