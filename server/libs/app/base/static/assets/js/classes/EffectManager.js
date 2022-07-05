import Toast from "./Toast.js";


// classes/EffectManager.js
export default class EffectManager {
    /**
     * Call API to get all effect IDs and set click listener for all effect buttons.
     * @param {Device|undefined} currentDevice
     */
    constructor(currentDevice) {
        /**
         * @type {Device}
         */
        this.currentDevice = currentDevice;

        if (!this.currentDevice) return;

        $.ajax({
            url: "/api/resources/effects",
            data: {}
        }).done((data) => {
            this.allEffects = Object.keys(data.special).concat(Object.keys(data.music), Object.keys(data.non_music))
            // Listen for effect change on click
            this.allEffects.forEach(effect => {
                $("#" + effect).on('click', () => {
                    this.switchEffect(effect);
                });
            });
        })
    }

    /**
     * Call API to set effect.
     * @param {string} effect
     */
    switchEffect(effect) {
        if (!this.allEffects.includes(effect)) return;

        $.ajax({
            url: "/api/effect/active",
            type: "POST",
            data: JSON.stringify({ "device": this.currentDevice.id, "effect": effect }),
            contentType: 'application/json;charset=UTF-8'
        }).done((data) => {
            // UI and State Updates should be here
            // this could cause Problems later
            this.currentDevice.setActiveEffect(data.effect);
            this.currentDevice.getCycleStatus();
        }).fail((data) => {
            console.log(JSON.stringify(data, null, '\t'));
            new Toast("Error while setting effect.").error();
        });
    }
}
