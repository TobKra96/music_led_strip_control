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

    getActiveEffect() {
        return $.ajax({
            url: "/api/effect/active",
            data: {
                "device": this.id
            }
        }).done((data) => {
            this.setActiveEffect(data["effect"]);
            return this._activeEffect;
        });
    }

    setActiveEffect(newActiveEffect) {
        this._activeEffect = newActiveEffect;

        $(".dashboard_effect_active").removeClass("dashboard_effect_active");
        $("#" + this._activeEffect).addClass("dashboard_effect_active");
        if (this._activeEffect != "") {
            const activeEffectText = $("#" + this._activeEffect).text();
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
                        // Clear all group pills
                        $("#device_groups").empty();
                        // Add device group pills
                        setting_value.forEach(group => {
                            const pill = `<span class="badge badge-primary badge-pill" value="${group}">${group} <span class="feather icon-x"></span></span> `;
                            $("#device_groups").append(pill);
                        });
                        // Clear all dropdown group options
                        $("#device_group_dropdown").empty();
                        // Populate device group dropdown with all available groups
                        jinja_groups.groups.forEach(group => {
                            let exists = 0 != $(`#device_groups span[value="${group}"]`).length;
                            const option = new Option(group, group);
                            if (!exists) {
                                $("#device_group_dropdown").prepend(option);
                            }
                        });
                        $("#device_group_dropdown")[0].selectedIndex = 0;
                    } else {
                        $(`#${setting_key}`).val(setting_value);
                    }
                    $(`#${setting_key}`).trigger('change');

                    // Set initial brightness slider value
                    $(`span[for='${setting_key}']`).text(setting_value)
                })
            });
    }

}
