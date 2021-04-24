// classes/Device.js
export default class Device {
    constructor(params) {
        Object.assign(this, params);
        // this.id = id;
        // this._name = name;
        this.activeEffect = "";
        this.settings = {};
        this.link = "";
    }

    set name(name) {
        this._name = name;
        // Update HTML elements on namechange
        if(this._link != undefined && this._link !== "") {
            this._link.innerHTML = name;
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
        this._link = link;
        return this._link;
    }

    getSetting(key) {
        //  returns promise
        return $.ajax({
            url: "/GetDeviceSetting",
            data: {
                "device": this.id,
                "setting_key": key,
            }
        })
    }

    getOutputSetting(key, type) {
        //  returns promise
        return $.ajax({
            url: "/GetOutputTypeDeviceSetting",
            data: {
                "device": this.id,
                "output_type_key": type,
                "setting_key": key,
            }
        });
    }

    getActiveEffect() {
        return $.ajax({
            url: "/GetActiveEffect",
            data: {
                "device": this.id
            }
        }).done((data) => {
            this.setActiveEffect(data["effect"]);
            return this.activeEffect;
        });
    }

    setActiveEffect(newActiveEffect) {
        this.activeEffect = newActiveEffect;
        $("#selected_device_txt").text(this.name);

        $(".dashboard_effect_active").removeClass("dashboard_effect_active");
        $("#" + this.activeEffect).addClass("dashboard_effect_active");
        if (this.activeEffect != "") {
            const activeEffectText = $("#" + this.activeEffect).text();
            $("#selected_effect_txt").text(activeEffectText);
        }

    }

}