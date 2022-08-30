import { Device } from "./classes/Device.js";
import Toast from "./classes/Toast.js";


$(() => {

    setThemeIcon(localStorage.theme);

    $("#theme-indicator").on("click", () => {
        toggleTheme();
    });

    if (!jinja_devices.length) {
        new Toast('No device found. Create a new device in "Device Settings".').info();
        return;
    }

    // Create Base Group ("all_devices").
    let devicesById = {};
    jinja_devices.forEach(device => { devicesById[device.id] = device.name });
    const baseGroup = new Device({ assigned_to: devicesById, id: "all_devices", name: "All Devices" });

    // Create Devices and Groups from Jinja output.
    const devices = jinja_devices.map(d => { return new Device(d) });
    const groups = [baseGroup].concat(jinja_groups.map(g => { return new Device(g) }));

    devices.concat(groups).forEach(item => {
        $(item.link).on('click', () => {
            // Async function
            item.getActiveEffect();
        });
    });

    // Add "Edit" button to effect buttons.
    const editButton = '<i class="feather icon-edit edit_button" aria-hidden="true"></i>';
    const activeIndicator = '<i class="active_indicator d-none" aria-hidden="true"></i>';
    $(editButton).insertAfter("#effect_random_cycle");
    $("#dashboard-list-none-music, #dashboard-list-music").children().each((_, element) => {
        $(editButton).appendTo($(element));
        $(activeIndicator).appendTo($(element)); // Also add active indicator.
    });

    $('.edit_button').on('click', e => {
        window.location.href = `/effects/${$(e.currentTarget).siblings()[0].id}`;
    });
    $(".edit_button").on("mouseover mouseout", e => {
        $($(e.currentTarget).siblings()[0]).toggleClass("dashboard_effect_hover");
    });

});

/**
 * Show corresponding theme icon.
 * @param {string} theme
 */
const setThemeIcon = (theme) => {
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
const toggleTheme = () => {
    if (localStorage.theme === "dark") {
        $("html").removeClass('dark');
        localStorage.theme = "light";
    } else {
        $("html").addClass('dark');
        localStorage.theme = "dark";
    }
    setThemeIcon(localStorage.theme);
}
