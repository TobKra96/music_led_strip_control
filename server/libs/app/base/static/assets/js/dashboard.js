import Device from "./classes/Device.js";
import EffectManager from "./classes/EffectManager.js";
import Toast from "./classes/Toast.js";

const effectManager = new EffectManager();

if (!jinja_devices.length) {
    new Toast('No device found. Create a new device in "Device Settings".').info()
} else {
    const devices = jinja_devices.map(d => { return new Device(d) });
    
    // Start with Fake Device
    devices.unshift(new Device({id:"all_devices", name:"All Devices" }))
    let currentDevice = devices[0];
    // Restore last selected device if there is any
    let lastDevice = devices.find(device => device.id === localStorage.getItem("lastDevice"));
    if (lastDevice instanceof Device) {
        currentDevice = lastDevice;
    }
    $(`a[data-device_id=${currentDevice.id}`).addClass("active");
    // Async function
    currentDevice.getActiveEffect();
    effectManager.currentDevice = currentDevice;
    
    // Build Device Tab
    devices.forEach(device => {
        // const link = device.getPill(currentDevice.id);
        $(`a[data-device_id=${device.id}`).on("click", () => {
            currentDevice = device;
            localStorage.setItem('lastDevice', device.id);
            effectManager.currentDevice = currentDevice;
            // Async function
            device.getActiveEffect();
        });

    });
}