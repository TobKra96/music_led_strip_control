import Device from "./classes/Device.js";
import Toast from "./classes/Toast.js";

if (!jinja_devices.length) {
    new Toast('No device found. Create a new device in "Device Settings".').info()
} else {
    // Start with Fake Device & create Devices from Jinja output
    const devices = [new Device({id:"all_devices", name:"All Devices" })];
    devices.concat(jinja_devices.map(d => { return new Device(d) }));
}