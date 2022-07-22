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

    // Add "Edit" button to effect buttons.
    let editButton = '<i class="feather icon-edit edit_button" aria-hidden="true"></i>';
    $(editButton).insertAfter("#effect_random_cycle");
    $("#dashboard-list-none-music, #dashboard-list-music").children().each((_, element) => {
        $(editButton).appendTo($(element));
    });

    $('.edit_button').on('click', (e) => {
        window.location.href = `/effects/${$(e.target).siblings()[0].id}`;
    });
    $(".edit_button").on("mouseover mouseout", (e) => {
        $($(e.target).siblings()[0]).toggleClass("dashboard_effect_hover");
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
