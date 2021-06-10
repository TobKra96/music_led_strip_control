import Device from "./classes/Device.js";
import Toast from "./classes/Toast.js";

if (!jinja_devices.length) {
    new Toast('No device found. Create a new device in "Device Settings".').info()
} else {
    // Start with Fake Device & create Devices from Jinja output
    const fake_device = [
        new Device({
            id: "all_devices",
            name: "All Devices"
        })
    ];
    const devices = fake_device.concat(jinja_devices.map(d => { return new Device(d) }));

    devices.forEach(device => {
        device.link.addEventListener('click', () => {
            // Async function
            device.getActiveEffect();
        });
    });

    // Select "All Devices" if localStorage is clear
    let currentDevice = devices.find(d => d.id === localStorage.getItem("lastDevice"));
    currentDevice = currentDevice ? currentDevice : devices[0];
    localStorage.setItem('lastDevice', currentDevice.id);
    $(`a[data-device_id=${currentDevice.id}`).addClass("active");
    $("#selected_device_txt").text(currentDevice.name);
    currentDevice.getActiveEffect();
}
