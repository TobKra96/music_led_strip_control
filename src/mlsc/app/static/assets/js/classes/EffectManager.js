import Toast from './Toast.js';


// classes/EffectManager.js
export default class EffectManager {
    /**
     * Call API to get all effect IDs and set click listener for all effect buttons.
     * @param {Device|undefined} currentDevice
     */
    constructor(currentDevice) {

        if (!['', 'dashboard'].includes(window.location.pathname.split("/").pop())) {
            return;
        }

        /**
         * @type {import('./Device').Device|undefined}
         */
        this.currentDevice = currentDevice;

        this.allEffects = [];

        $.ajax('/api/resources/effects').done((data) => {
            this.allEffects = [
                ...Object.keys(data.special),
                ...Object.keys(data.music),
                ...Object.keys(data.non_music)
            ];
            // Listen for effect change on click.
            this.allEffects.forEach(effect => {
                $(`#${effect}`).on('click', () => {
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

        const data = this._apiDataBuilder(effect);

        $.ajax({
            url: "/api/effect/active",
            type: "POST",
            data: JSON.stringify(data),
            contentType: 'application/json;charset=UTF-8'
        }).done((data) => {
            // UI and State Updates should be here.
            this.currentDevice.setCycleStatusStyle();

            if (data.devices) {
                this.currentDevice.setActiveEffectStyle(data.devices.map(x => x.effect));
            } else if (data.effect) {
                this.currentDevice.setActiveEffectStyle([data.effect]);
            }

        }).fail((data) => {
            console.log(JSON.parse(data.responseText));
            new Toast("Error while setting effect.").error();
        });
    }

    /**
     * Build a POST request data object for setting an effect.
     * @param {string} effect
     * @returns {{effect: string} | {devices: {device: string, effect: string}[]} | {device: string, effect: string}}
    */
    _apiDataBuilder(effect) {
        if (this.currentDevice.id === 'all_devices') {  // For all devices.
            return { effect };
        }

        if (this.currentDevice.isGroup) {  // For all devices in a group.
            const assignedDevices = jinja_groups.find(g => g.id === this.currentDevice.id).assigned_to;
            const devices = Object.keys(assignedDevices).map(device => ({
                device,
                effect
            }));
            return { devices };
        }

        // For single device.
        return { device: this.currentDevice.id, effect };
    }
}
