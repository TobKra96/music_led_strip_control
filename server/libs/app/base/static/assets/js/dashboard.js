import Device from "./classes/Device.js";
import Toast from "./classes/Toast.js";


$(function () {

    setThemeIcon(localStorage.theme);

    $("#theme-indicator").on("click", () => {
        toggleTheme();
    });

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

/**
 * Show corresponding theme icon.
 * @param {string} theme
 */
let setThemeIcon = (theme) => {
    if (theme === "dark") {
        $("#theme-indicator").addClass("icon-sun");
        $("#theme-indicator").removeClass("icon-moon");
    } else {
        $("#theme-indicator").addClass("icon-moon");
        $("#theme-indicator").removeClass("icon-sun");
    }
}

/**
 * Toggle theme and save to localStorage.
 */
let toggleTheme = () => {
    if (localStorage.theme === "dark") {
        $("html").removeClass('dark');
        localStorage.theme = "light";
    } else {
        $("html").addClass('dark');
        localStorage.theme = "dark";
    }
    setThemeIcon(localStorage.theme);
}
