import Tagin from "../../plugins/tagin/js/tagin.js";
import EffectManager from "./EffectManager.js";
const effectManager = new EffectManager();

// Do not init tagin if it is not on the page.
const taginEl = document.querySelector(".tagin")
const tagin = taginEl === null || taginEl === undefined ? undefined : new Tagin(taginEl);

// classes/Device.js
class Device {
    /**
     * Create a device.
     * @param {Object} params Device parameters.
     * @param {Object} params.assigned_to
     * @param {string} params.id
     * @param {string} params.name
     */
    constructor(params) {
        Object.assign(this, params);
        // this.id = id;
        // this._name = name;
        this.isGroup = this.id.startsWith("group_") || this.id === "all_devices";
        this.link = $(`a[data-device_id=${this.id}`)[0];

        // Insert Base Device ("all_devices") into localStorage if "lastDevice" does not exist yet.
        !('lastDevice' in localStorage) && localStorage.setItem("lastDevice", this.id);

        // Select last selected device if there is any.
        this.isCurrent && (
            this._activate(),
            $(`a[data-device_id=${this.id}`).addClass("active"),
            // Async function
            this.getActiveEffect()
        );

        // Add basic behavior to Pills
        $(`a[data-device_id=${this.id}`).on("click", e => {
            this.link = e.currentTarget;
            this._activate();
        });
    }

    /**
     * Set active device in device bar and save it to localStorage.
     */
    _activate() {
        $("#selected_type").text("Device");
        if (this.isGroup) {
            $("#selected_type").text("Group");
        }
        $("#selected_device_txt").text(this.name);
        localStorage.setItem('lastDevice', this.id);
        effectManager.currentDevice = this;
    }

    /**
     * Getter to check if the selected device  matches `lastDevice` in the localStorage.
     * @return {boolean}
     */
    get isCurrent() {
        return this.id === localStorage.getItem("lastDevice");
    }

    /**
     * Set new device name.
     * @param {string} name
     */
    set name(name) {
        this._name = name;
        // Update HTML elements on namechange
        if (this.link != undefined && this.link !== "") {
            this.link.innerHTML = name;
        }
    }

    /**
     * Get device name.
     * @return {string}
     */
    get name() {
        return this._name;
    }

    /**
     * Get current device pill from device bar.
     * @param {string} currentDeviceId
     * @return {jQuery.HTMLElement}
     */
    getPill(currentDeviceId) {
        const active = currentDeviceId === this.id ? " active" : "";
        const link = document.createElement("a");
        link.classList = "nav-link" + active;
        link.innerHTML = this.name;
        link.href = `#pills-${this.id}`;
        link.role = "tab";
        link.setAttribute("data-toggle", "pill");
        link.setAttribute("aria-controls", `pills-${this.id}`);
        link.setAttribute("aria-selected", "false");
        this.link = link;
        return this.link;
    }

    /**
     * Call API to get all device settings.
     * @param {string} excludedKey
     * @return {jQuery.jqXHR}
     */
    getSettings(excludedKey = "") {
        let settings = {
            "device": this.id
        };
        if (excludedKey !== "") {
            settings.excluded_key = excludedKey;
        }
        return $.ajax({
            url: "/api/settings/device",
            data: settings
        });
    }

    /**
     * Call API to get all device output settings.
     * @return {jQuery.jqXHR}
     */
    getOutputSettings() {
        return $.ajax({
            url: "/api/settings/device/output-type",
            data: {
                "device": this.id
            }
        });
    }

    /**
     * Call API to get all effect settings.
     * @param {string} effectIdentifier
     * @return {jQuery.jqXHR}
     */
    getEffectSettings(effectIdentifier) {
        return $.ajax({
            url: "/api/settings/effect",
            data: {
                "device": this.id,
                "effect": effectIdentifier
            }
        });
    }

    /**
     * Call API to get the `Random Cycle` effect status.
     * @return {jQuery.jqXHR}
     */
    getCycleStatus() {
        // TODO: Implement UI/UX for multiple devices with active `Random Cycle`.
        return $.ajax({
            url: "/api/effect/cycle-status",
            data: {
                "device": this.id
            }
        }).done((data) => {
            this.setCycleStatusStyle(data.random_cycle_active);
        });
    }

    /**
     * Set border style for `Random Cycle` button.
     * @param {boolean} isCycleActive
     */
    setCycleStatusStyle(isCycleActive) {
        if (isCycleActive) {
            $("#effect_random_cycle").addClass("active")
        } else {
            $("#effect_random_cycle").removeClass("active")
        }
    }

    /**
     * Call API to get the active effect for a device.
     * @return {jQuery.jqXHR}
     */
    getActiveEffect() {
        this.getCycleStatus();
        return $.ajax({
            url: "/api/effect/active",
            data: {
                "device": this.id
            }
        }).done((data) => {
            this.setActiveEffectStyle(data.effect);
        });
    }

    /**
     * Show indicator dot on effect buttons which are active.
     */
    setDeviceIndicators() {
        $.ajax("/api/effect/active").done((data) => {
            // Group devices by effect.
            const result = data.devices.reduce((group, device) => {
                const { effect } = device;
                group[effect] = group[effect] ?? [];
                group[effect].push(device);
                return group;
            }, {});

            // Insert device names into active indicator title.
            $(".active_indicator").addClass("d-none");
            Object.entries(result).forEach(([effect, devices]) => {
                let grouped = [];
                Object.values(devices).forEach((item) => {
                    // BUG: Error when newly created device is undefined.
                    let deviceName = jinja_devices.find(d => d.id === item.device).name;
                    grouped.push(deviceName);
                });
                // TODO: Clicking the dot should show a list of devices with that effect.
                // Currently only shows devices on hover in a title.
                $(`#${effect}`).siblings(".active_indicator").removeClass("d-none").attr("title", grouped.join(", "));
            });
        });
    }

    /**
     * Set style for active effect buttons and update device bar data.
     * @param {string|Array.<string>} newActiveEffect Effect or array of effects.
     */
    setActiveEffectStyle(newActiveEffect) {

        // WIP: Not working yet.
        // setDeviceIndicators();

        if (newActiveEffect instanceof Array) {
            $(".dashboard_effect_active").removeClass("dashboard_effect_active");
            $("#selected_effect_txt").text("Multiple Effects");
            newActiveEffect.forEach((effect) => {
                $("#" + effect).addClass("dashboard_effect_active");
            });
            return;
        }

        $(".dashboard_effect_active").removeClass("dashboard_effect_active");
        $("#" + newActiveEffect).addClass("dashboard_effect_active");
        if (newActiveEffect !== "") {
            const activeEffectText = $("#" + newActiveEffect).text().trim();
            $("#selected_effect_txt").text(activeEffectText);
        }

    }

    /**
     * Populate forms with data from config.
     */
    refreshConfig() {
        this.getSettings("effects").then((response) => {
            Object.entries(response.settings).forEach(([key, value]) => {
                if ($("#" + key).attr('type') === 'checkbox') {
                    $("#" + key).prop('checked', value);
                } else if ($("#" + key).attr('type') === 'option') {
                    populateDeviceGroups(value);
                    populateGlobalGroups(Object.values(value));
                } else {
                    $("#" + key).val(value);
                }
                // Set initial brightness slider value
                // because it is the only slider label on the page
                $(`span[for='${key}']`).text(value);

                $("#" + key).trigger('change');
            });
        });

        this.getOutputSettings().then((response) => {
            Object.entries(response.output_settings).forEach(([key, value]) => {
                if ($("#" + key).attr('type') === 'checkbox') {
                    $("#" + key).prop('checked', value);
                } else {
                    $("#" + key).val(value);
                }

                $("#" + key).trigger('change');
            });
        });
    }

}

/**
 * Populate selected device groups on Device Settings page.
 * @param {Object} deviceGroups
 */
function populateDeviceGroups(deviceGroups) {
    tagin.clearTags();
    tagin.addTag(deviceGroups);
    if (Object.keys(deviceGroups).length > 0) {
        $('#device_group_pills').removeClass("d-none");
    }
}

/**
 * Populate global device groups dropdown on Device Settings page.
 * @param {Array.<string>} deviceGroups
 */
function populateGlobalGroups(deviceGroups) {
    // Clear all dropdown group options
    $("#device_group_dropdown").empty();
    // Populate device group dropdown with all available groups
    Object.entries(jinja_groups.groups).forEach(([groupId, globalGroup]) => {
        if (!deviceGroups.includes(globalGroup)) {
            $("#device_group_dropdown").append(`<option tag-id="${groupId}" value="${globalGroup}">${globalGroup}</option>`);
        }
    });
    // Add placeholder option on top
    $("#device_group_dropdown").prepend(`<option value="placeholder" disabled selected>Select a group</option>`);
    $("#device_group_dropdown")[0].selectedIndex = 0;
}

export { Device, tagin };
