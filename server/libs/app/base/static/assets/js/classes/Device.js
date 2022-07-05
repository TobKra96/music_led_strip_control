import EffectManager from "./EffectManager.js";
const effectManager = new EffectManager();

// classes/Device.js
export default class Device {
    /**
     * Create a device.
     * @param {{groups: array<string>, id: string, name: string}} params
     */
    constructor(params) {
        Object.assign(this, params);
        // this.id = id;
        // this._name = name;
        this._activeEffect = "";
        this.link = $(`a[data-device_id=${this.id}`)[0];
        this._isCurrent = this.id === localStorage.getItem("lastDevice");

        // Insert first device ("all_devices") into localStorage if "lastDevice" does not exist yet
        !('lastDevice' in localStorage) && localStorage.setItem("lastDevice", this.id);
        // Select last selected device if there is any
        this.id === localStorage.getItem("lastDevice") && (
            this._activate(),
            $(`a[data-device_id=${this.id}`).addClass("active"),
            // Async function
            this.getActiveEffect()
        );

        // Add basic behavior to Pills
        const self = this;
        $(`a[data-device_id=${this.id}`).on("click", function () {
            self.link = this;
            self._activate();
        });
    }

    /**
     * Set active device in device bar and save it to localStorage.
     */
    _activate() {
        $("#selected_device_txt").text(this.name);
        localStorage.setItem('lastDevice', this.id);
        effectManager.currentDevice = this;
    }

    /**
     * Getter to check if the selected device  matches `lastDevice` in the localStorage.
     * @return {boolean}
     */
    get isCurrent() {
        return this._isCurrent;
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
     * Call API to get a all effect settings.
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
        return $.ajax({
            url: "/api/effect/cycle-status",
            data: {
                "device": this.id
            }
        }).done((data) => {
            this.setCycleStatus(data.random_cycle_active);
        });
    }

    /**
     * Set border style for `Random Cycle` button.
     * @param {boolean} isCycleActive
     */
    setCycleStatus(isCycleActive) {
        if (isCycleActive) {
            $("#effect_random_cycle").css("box-shadow", "inset 0 0 0 3px #3f4d67");
        } else {
            $("#effect_random_cycle").css("box-shadow", "0 1px 20px 0 rgb(69 90 100 / 8%)");
        }
    }

    /**
     * Call API to get the active effect for a device.
     * @return {jQuery.jqXHR}
     */
    getActiveEffect() {
        return $.ajax({
            url: "/api/effect/active",
            data: {
                "device": this.id
            }
        }).done((data) => {
            this.setActiveEffect(data["effect"]);
            this.getCycleStatus();
        });
    }

    /**
     * Set style for selected effect button and device bar.
     * @param {string} newActiveEffect
     */
    setActiveEffect(newActiveEffect) {
        this._activeEffect = newActiveEffect;

        $(".dashboard_effect_active").removeClass("dashboard_effect_active");
        $("#" + this._activeEffect).addClass("dashboard_effect_active");
        if (this._activeEffect != "") {
            const activeEffectText = $("#" + this._activeEffect).text().trim();
            $("#selected_effect_txt").text(activeEffectText);
        }

    }

    /**
     * Populate forms with data from config.
     */
    refreshConfig() {
        this.getSettings("effects").then((response) => {
            Object.entries(response.settings).forEach(([key, value]) => {
                if ($("#" + key).attr('type') == 'checkbox') {
                    $("#" + key).prop('checked', value);
                } else if ($("#" + key).attr('type') == 'option') {
                    populateDeviceGroups(value);
                    populateGlobalGroups(value);
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
                if ($("#" + key).attr('type') == 'checkbox') {
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
 * @param {Array.<string>} deviceGroups
 */
function populateDeviceGroups(deviceGroups) {
    // Manually trigger change event to update device groups
    const target = document.querySelector('#device_groups');
    target.value = deviceGroups.join(",");
    target.dispatchEvent(new Event('change'));
    // Show device group block if there are groups
    if (deviceGroups.length > 0) {
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
    jinja_groups.groups.forEach(globalGroup => {
        if (!deviceGroups.includes(globalGroup)) {
            $("#device_group_dropdown").prepend(`<option value="${globalGroup}">${globalGroup}</option>`);
        }
    });
    // Add placeholder option on top
    $("#device_group_dropdown").prepend(`<option value="placeholder" disabled selected>Select a group</option>`);
    $("#device_group_dropdown")[0].selectedIndex = 0;
}
