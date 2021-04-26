import Device from "./classes/Device.js";
import Toast from "./classes/Toast.js";

if (!jinja_devices.length) {
    new Toast('No device found. Create a new device in "Device Settings".').info()
} else {
    // Start with Fake Device & create Devices from Jinja output
    const fake_device = [new Device({id:"all_devices", name:"All Devices" })];
    const devices = fake_device.concat(jinja_devices.map(d => { return new Device(d) }));

    devices.forEach(device => {
        device.link.addEventListener('click', () => {
            // Async function
            device.getActiveEffect();
        });
    });
}