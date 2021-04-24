import Device from "./classes/Device.js";
import EffectManager from "./classes/EffectManager.js";
import Toast from "./classes/Toast.js";


if (!jinja_devices.length) {
    new Toast('No device found. Create a new device in "Device Settings".').info()
} else {
    // Start with Fake Device
    const fake_device = new Device({id:"all_devices", name:"All Devices" });
    const effectManager = new EffectManager(fake_device);
    // Create Devices from Jinja
    const devices = jinja_devices.map(d => { return new Device(d, effectManager) });
    devices.unshift(fake_device);
    
    // Add Behavior to Device Tab
    devices.forEach(device => {
        $(`a[data-device_id=${device.id}`).on("click", function() {
            device.link = this;
            localStorage.setItem('lastDevice', device.id);
            effectManager.currentDevice = device;
            // Async function
            device.getActiveEffect();
        });

    });
}