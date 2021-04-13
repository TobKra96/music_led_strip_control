// classes/Device.js
export class Device {
    constructor(id, name) {
        this.id = id;
        this.name = name;
        this.activeEffect = "";
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

        $(".dashboard_effect_active").removeClass("dashboard_effect_active");
        $("#" + this.activeEffect).addClass("dashboard_effect_active");
        if (this.activeEffect != "") {
            const activeEffectText = $("#" + this.activeEffect).text();
            $("#selected_effect_txt").text(activeEffectText);
        }

    }

}