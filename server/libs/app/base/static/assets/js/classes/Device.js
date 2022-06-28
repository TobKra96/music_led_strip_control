import EffectManager from "./EffectManager.js";
const effectManager = new EffectManager();

// classes/Device.js
export default class Device {
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

    _activate() {
        $("#selected_device_txt").text(this.name);
        localStorage.setItem('lastDevice', this.id);
        effectManager.currentDevice = this;
    }

    get isCurrent() {
        return this._isCurrent;
    }

    set name(name) {
        this._name = name;
        // Update HTML elements on namechange
        if (this.link != undefined && this.link !== "") {
            this.link.innerHTML = name;
        }
    }

    get name() {
        return this._name;
    }

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

    setCycleStatus(isCycleActive) {
        if (isCycleActive) {
            $("#effect_random_cycle").css("box-shadow", "inset 0 0 0 3px #3f4d67");
        } else {
            $("#effect_random_cycle").css("box-shadow", "0 1px 20px 0 rgb(69 90 100 / 8%)");
        }
    }

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

    setActiveEffect(newActiveEffect) {
        this._activeEffect = newActiveEffect;

        $(".dashboard_effect_active").removeClass("dashboard_effect_active");
        $("#" + this._activeEffect).addClass("dashboard_effect_active");
        if (this._activeEffect != "") {
            const activeEffectText = $("#" + this._activeEffect).text().trim();
            $("#selected_effect_txt").text(activeEffectText);
        }

    }

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
