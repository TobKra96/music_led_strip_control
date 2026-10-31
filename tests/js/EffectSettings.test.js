import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../src/mlsc/app/static/assets/js/classes/Api.js', () => ({
    api: { get: vi.fn(), patch: vi.fn() },
}));

import { api } from '../../src/mlsc/app/static/assets/js/classes/Api.js';
import { loadEffectSettings, saveEffectSettings } from '../../src/mlsc/app/static/assets/js/classes/EffectSettings.js';

const device = { id: 'device_0', isGroup: false, assigned_to: {} };
const group = { id: 'group_1', isGroup: true, assigned_to: { device_2: 'Desk', device_0: 'Shelf' } };
const empty = { id: 'group_2', isGroup: true, assigned_to: {} };

beforeEach(() => {
    vi.resetAllMocks();
});

describe('loadEffectSettings', () => {
    it('loads the settings of a single device', async () => {
        api.get.mockResolvedValue({ speed: 5 });

        await expect(loadEffectSettings(device, 'effect_wave')).resolves.toEqual({ speed: 5 });
        expect(api.get).toHaveBeenCalledWith('/devices/device_0/effects/effect_wave/settings');
    });

    it('loads the settings of the first device of a group', async () => {
        api.get.mockResolvedValue({ speed: 7 });

        await expect(loadEffectSettings(group, 'effect_wave')).resolves.toEqual({ speed: 7 });
        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenCalledWith('/devices/device_2/effects/effect_wave/settings');
    });

    it('resolves null for a group without devices', async () => {
        await expect(loadEffectSettings(empty, 'effect_wave')).resolves.toBeNull();
        expect(api.get).not.toHaveBeenCalled();
    });
});

describe('saveEffectSettings', () => {
    it('patches a single device', async () => {
        api.patch.mockResolvedValue({});

        await saveEffectSettings(device, 'effect_wave', { speed: 3 });

        expect(api.patch).toHaveBeenCalledWith('/devices/device_0/effects/effect_wave/settings', { speed: 3 });
    });

    it('patches every device of a group', async () => {
        api.patch.mockResolvedValue({});

        await saveEffectSettings(group, 'effect_wave', { speed: 3 });

        expect(api.patch).toHaveBeenCalledTimes(2);
        expect(api.patch).toHaveBeenCalledWith('/devices/device_2/effects/effect_wave/settings', { speed: 3 });
        expect(api.patch).toHaveBeenCalledWith('/devices/device_0/effects/effect_wave/settings', { speed: 3 });
    });

    it('rejects for a group without devices without calling the API', async () => {
        await expect(saveEffectSettings(empty, 'effect_wave', {})).rejects.toThrow('no devices');
        expect(api.patch).not.toHaveBeenCalled();
    });

    it('names the devices that failed while the others are still saved', async () => {
        api.patch.mockImplementation(path => path.includes('device_2') ? Promise.reject(new Error('boom')) : Promise.resolve({}));

        await expect(saveEffectSettings(group, 'effect_wave', {})).rejects.toThrow('Desk');
        expect(api.patch).toHaveBeenCalledTimes(2);
    });
});
