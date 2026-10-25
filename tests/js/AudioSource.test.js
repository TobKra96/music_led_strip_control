import { describe, expect, it } from 'vitest';
import { BROWSER_NATIVE_RATE, BROWSER_SAMPLE_RATES, listeningTo, sectionsFor } from '../../src/mlsc/app/static/assets/js/classes/AudioSource.js';

describe('sectionsFor', () => {
    it('shows the Device dropdown for a server device only', () => {
        expect(sectionsFor('device')).toEqual({ device: true, browser: false });
    });

    it('shows the stream button for this browser only', () => {
        expect(sectionsFor('browser')).toEqual({ device: false, browser: true });
    });
});

describe('listeningTo', () => {
    const browser = { source: 'browser', device_name: null };
    const device = { source: 'device', device_name: 'Mikrofon (Realtek)' };

    it('says this browser is not streaming yet before any status or while waiting', () => {
        expect(listeningTo(browser, null)).toBe('Listening to: this browser (not streaming yet)');
        expect(listeningTo(browser, { state: 'waiting', device: 'Browser Microphone' })).toBe('Listening to: this browser (not streaming yet)');
    });

    it('says this browser once audio arrives', () => {
        expect(listeningTo(browser, { state: 'ok', device: 'Browser Microphone' })).toBe('Listening to: this browser');
    });

    it('names the device the audio process opened', () => {
        expect(listeningTo(device, { state: 'ok', device: 'Mikrofon (Realtek) (WASAPI)' })).toBe('Listening to: Mikrofon (Realtek) (WASAPI)');
        expect(listeningTo(device, { state: 'starting', device: 'Mikrofon (Realtek)' })).toBe('Listening to: Mikrofon (Realtek)');
    });

    it('names the saved device, or the system default, without a status', () => {
        expect(listeningTo(device, null)).toBe('Listening to: Mikrofon (Realtek)');
        expect(listeningTo({ source: 'device', device_name: null }, null)).toBe('Listening to: the system default device');
    });

    it('says when the device does not work', () => {
        expect(listeningTo(device, { state: 'error', device: 'Mikrofon (Realtek)' })).toBe('Listening to: nothing, the device does not work');
    });
});

describe('browser sample rates', () => {
    it('offer the native rate among the common ones', () => {
        expect(BROWSER_SAMPLE_RATES).toContain(BROWSER_NATIVE_RATE);
    });
});
