import EffectManager from "./EffectManager.js";
const effectManager = new EffectManager();

// classes/Device.js
export default class Device {
    /**
     * Create a device.
     * @param {{id: string, name: string}} params
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
     * Call API to get a single setting of a device.
     * @param {string} key
     * @return {jQuery.jqXHR}
     */
    getSetting(key) {
        //  returns promise
        return $.ajax({
            url: "/api/settings/device",
            data: {
                "device": this.id,
                "setting_key": key,
            }
        })
    }

    /**
     * Call API to get a single output setting of a device.
     * @param {string} key
     * @param {string} type
     * @return {jQuery.jqXHR}
     */
    getOutputSetting(key, type) {
        //  returns promise
        return $.ajax({
            url: "/api/settings/device/output-type",
            data: {
                "device": this.id,
                "setting_key": key,
                "output_type_key": type,
            }
        });
    }

    /**
     * Call API to get a single setting of an effect.
     * @param {string} effectIdentifier
     * @param {string} key
     * @return {jQuery.jqXHR}
     */
    getEffectSetting(effectIdentifier, key) {
        return $.ajax({
            url: "/api/settings/effect",
            data: {
                "device": this.id,
                "effect": effectIdentifier,
                "setting_key": key,
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
            return this._activeEffect;
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
     * @param {{output_raspi: string, output_udp: string}} output_types
     */
    refreshConfig(output_types) {

        if (!output_types) return;
        // fetch Device Config data from Server and update the Form
        const device_config_input = $(".device_setting_input").map(function () { return this.id }).toArray()
            .map(id => this.getSetting(id));
        const device_config_output = Object.keys(output_types).flatMap(output_type_key => {
            return $("." + output_type_key).map(function () { return this.id }).toArray()
                .map(key => this.getOutputSetting(key, output_type_key))
        });
        Promise.all(
            device_config_input
                .concat(device_config_output)
        )
            .then((response) => {
                // response array contains ALL current device config objects
                response.forEach(data => {
                    const setting_key = data["setting_key"];
                    const setting_value = data["setting_value"];
                    $("#" + setting_key).trigger('change');

                    if ($(`#${setting_key}`).attr('type') == 'checkbox') {
                        $(`#${setting_key}`).prop('checked', setting_value);
                    } else if ($(`#${setting_key}`).attr('type') == 'option') {
                        populateDeviceGroups(setting_value);
                        populateGlobalGroups(setting_value);
                    } else {
                        $(`#${setting_key}`).val(setting_value);
                    }
                    $(`#${setting_key}`).trigger('change');

                    // Set initial brightness slider value
                    $(`span[for='${setting_key}']`).text(setting_value);
                })
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
        const option = new Option(globalGroup, globalGroup);
        if (!deviceGroups.includes(globalGroup)) {
            $("#device_group_dropdown").prepend(option);
        }
    });
    // Add placeholder option on top
    $("#device_group_dropdown").prepend(`<option value="placeholder" disabled selected>Select a group</option>`);
    $("#device_group_dropdown")[0].selectedIndex = 0;
}
