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
        if (!this.allEffects.includes(effect) || !this.currentDevice) return;

        const data = {};

        if (this.currentDevice.isGroup && this.currentDevice.id !== "all_devices") {
            // Set effect for all devices in a group.
            const assignedDevices = jinja_groups.find(g => g.id === this.currentDevice.id).assigned_to;
            data.devices = [];
            Object.keys(assignedDevices).forEach(device => {
                data.devices.push({
                    "device": device,
                    "effect": effect
                });
            });
        } else {
            // Set effect for single device.
            data.device = this.currentDevice.id;
            data.effect = effect;
        }

        $.ajax({
            url: "/api/effect/active",
            type: "POST",
            data: JSON.stringify(data),
            contentType: 'application/json;charset=UTF-8'
        }).done((data) => {
            // UI and State Updates should be here

            let activeEffect;
            if (data.devices) {
                // Get first device's effect since all devices in the group should have the same effect.
                activeEffect = data.devices[0].effect;
            } else if (data.effect) {
                activeEffect = data.effect;
            }
            this.currentDevice.setActiveEffectStyle(activeEffect);
            this.currentDevice.getCycleStatus();
        }).fail((data) => {
            console.log(JSON.stringify(data, null, '\t'));
            new Toast("Error while setting effect.").error();
        });
    }
}
