import { api } from './Api.js';

/**
 * Ids of the devices an effect setting applies to: the members of a group, or the device itself.
 * @param {{id: string, isGroup: boolean, assigned_to: Object.<string, string>}} target
 * @return {Array.<string>}
 */
const deviceIds = target => target.isGroup ? Object.keys(target.assigned_to) : [target.id];

const settingsPath = (deviceId, effectId) => `/devices/${deviceId}/effects/${effectId}/settings`;

/**
 * Load the settings of one effect. A group shows the settings of its first device.
 * @param {{id: string, isGroup: boolean, assigned_to: Object.<string, string>}} target Device or group.
 * @param {string} effectId
 * @return {Promise.<object | null>} `null` for a group without devices.
 */
export const loadEffectSettings = async (target, effectId) => {
    const [first] = deviceIds(target);
    return first === undefined ? null : api.get(settingsPath(first, effectId));
};

/**
 * Save the settings of one effect. A group applies them to every device, and a device that fails does not stop the others.
 * @param {{id: string, isGroup: boolean, assigned_to: Object.<string, string>}} target Device or group.
 * @param {string} effectId
 * @param {object} settings
 * @return {Promise} Rejects when the group has no devices, or with the names of the devices that failed.
 */
export const saveEffectSettings = async (target, effectId, settings) => {
    const ids = deviceIds(target);
    if (!ids.length) {
        throw new Error('This group has no devices.');
    }
    const results = await Promise.allSettled(ids.map(id => api.patch(settingsPath(id, effectId), settings)));
    const failed = ids.filter((_, i) => results[i].status === 'rejected');
    if (failed.length) {
        const names = failed.map(id => target.assigned_to[id] ?? id).join(', ');
        throw new Error(`Could not save to ${names}.`);
    }
};
