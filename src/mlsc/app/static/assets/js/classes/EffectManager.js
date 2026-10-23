import { api } from './Api.js';
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

        api.get('/resources/effects').then((data) => {
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

        this._request(effect).then((active) => {
            // UI and State Updates should be here.
            this.currentDevice.setCycleStatusStyle();
            this.currentDevice.setActiveEffectStyle(active.map(x => x.effect));
        }).catch((error) => {
            new Toast(`Error while setting effect. ${error.summary}`).error();
        });
    }

    /**
     * Call API to set the effect of the current device, group or all devices.
     * @param {string} effect
     * @return {Promise.<Array.<{device_id: string, effect: string}>>} The devices that changed.
     */
    _request(effect) {
        if (this.currentDevice.id === 'all_devices') {  // For all devices.
            return api.put('/effect', { effect });
        }

        if (this.currentDevice.isGroup) {  // For all devices in a group.
            return api.put('/effect', { effect, device_ids: Object.keys(this.currentDevice.assigned_to) });
        }

        // For single device.
        return api.put(`/devices/${this.currentDevice.id}/effect`, { effect }).then(x => [x]);
    }
}
