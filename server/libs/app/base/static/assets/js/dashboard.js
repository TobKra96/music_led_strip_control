import Device from "./classes/Device.js";
import EffectManager from "./classes/EffectManager.js";
import Toast from "./classes/Toast.js";


if (!jinja_devices.length) {
    new Toast('No device found. Create a new device in "Device Settings".').info()
} else {
    const devices = jinja_devices.map(d => { return new Device(d) });
    
    // Start with Fake Device
    devices.unshift(new Device({id:"all_devices", name:"All Devices" }))
    let currentDevice = devices[0];
    // Select last selected device if there is any
    let lastDevice = devices.find(device => device.id === localStorage.getItem("lastDevice"));
    if (lastDevice instanceof Device) {
        currentDevice = lastDevice;
    }
    $(`a[data-device_id=${currentDevice.id}`).addClass("active");
    
    const effectManager = new EffectManager(currentDevice);
    // Async function
    currentDevice.getActiveEffect();
    
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