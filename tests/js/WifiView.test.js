import { describe, expect, it } from 'vitest';
import { ROLLBACK_SECONDS, addressOf, operationView, pageView, secondsLeft, signalLabel } from '../../src/mlsc/app/static/assets/js/classes/WifiView.js';

const ready = {
    supported: true, hotspot_supported: true, country: 'DE', interface: 'wlan0', radio: 'ready',
    diagnosis: { status: 'ok', message: 'Wi-Fi is ready (country DE).', suggested_fix: null },
    mode: 'client', connected: true, ssid: 'Home', ip: '192.168.1.50', hotspot: null,
};
const session = { authenticated: true, pin_required: true };
const warning = (message, fix = null) => ({ status: 'warning', message, suggested_fix: fix });

describe('pageView', () => {
    it('shows the whole page and no banner for a ready radio', () => {
        const view = pageView(ready, session);

        expect(view).toMatchObject({ banner: null, showClient: true, showHotspot: true, showRadioButton: false, authWarning: false });
        expect(view.summary).toBe('Connected to Home, IP address 192.168.1.50.');
        expect(view.interface).toBe('wlan0');
    });

    it('hides everything but the banner without NetworkManager', () => {
        const view = pageView({ ...ready, supported: false, diagnosis: warning('NetworkManager is not available, so MLSC cannot manage Wi-Fi.', 'Install NetworkManager or manage Wi-Fi yourself.') }, session);

        expect(view.unsupported).toBe(true);
        expect(view).toMatchObject({ showClient: false, showHotspot: false, showStatus: false });
        expect(view.banner.text).toContain('NetworkManager is not available');
    });

    it('offers the switch-on button only for a switched off radio and hides the controls', () => {
        const fix = 'Turn it on from the Wi-Fi page, or run: sudo nmcli radio wifi on';
        const view = pageView({ ...ready, radio: 'switched_off', diagnosis: warning('Wi-Fi is switched off.', fix) }, session);

        expect(view).toMatchObject({ showRadioButton: true, showClient: false, showHotspot: false });
        expect(view.banner).toEqual({ level: 'warning', text: 'Wi-Fi is switched off.', fix });
    });

    it.each(['blocked', 'unavailable', 'no_adapter'])('shows the warning without a button for %s', (radio) => {
        const view = pageView({ ...ready, radio, diagnosis: warning('Problem.', 'Fix.') }, session);

        expect(view).toMatchObject({ showRadioButton: false, showClient: false, showHotspot: false });
        expect(view.banner.text).toBe('Problem.');
    });

    it('hides only the Hotspot card when the adapter cannot run a Hotspot', () => {
        const view = pageView({ ...ready, hotspot_supported: false, diagnosis: warning('The Wi-Fi adapter does not support the Hotspot.') }, session);

        expect(view).toMatchObject({ showClient: true, showHotspot: false });
        expect(view.banner.level).toBe('warning');
    });

    it('keeps the Hotspot card for a missing country, which only warns', () => {
        const view = pageView({ ...ready, country: null, diagnosis: warning('The Wi-Fi country is not set, so the radio may be blocked.') }, session);

        expect(view).toMatchObject({ showClient: true, showHotspot: true });
        expect(view.banner).not.toBeNull();
    });

    it('warns that anyone on the network can change the settings while the PIN lock is off', () => {
        expect(pageView(ready, { authenticated: false, pin_required: false }).authWarning).toBe(true);
    });

    it('summarises the Hotspot with its name', () => {
        const view = pageView({ ...ready, mode: 'hotspot', connected: false, ssid: null, ip: '10.42.0.1', hotspot: { ssid: 'MLSC-1234', password: 'abcd1234' } }, session);

        expect(view.summary).toBe('Hotspot MLSC-1234 is on, IP address 10.42.0.1.');
        expect(view.hotspot).toEqual({ ssid: 'MLSC-1234', password: 'abcd1234' });
    });

    it('summarises a Pi without a connection', () => {
        expect(pageView({ ...ready, connected: false, ssid: null, ip: null }, session).summary).toBe('Not connected to a Wi-Fi network.');
    });

    it('has no Hotspot password when the API did not return one', () => {
        const view = pageView({ ...ready, mode: 'hotspot', hotspot: { ssid: 'MLSC-1234', password: null } }, session);

        expect(view.hotspot.password).toBeNull();
    });
});

describe('addressOf', () => {
    it('builds the mlsc.local address with the port of the page', () => {
        expect(addressOf({ port: '8080' })).toBe('http://mlsc.local:8080');
    });

    it('leaves out a default port', () => {
        expect(addressOf({ port: '' })).toBe('http://mlsc.local');
    });
});

describe('secondsLeft', () => {
    it('counts down the Wi-Fi Rollback from 45 seconds and stops at zero', () => {
        expect(ROLLBACK_SECONDS).toBe(45);
        expect(secondsLeft(1000, 1000)).toBe(45);
        expect(secondsLeft(1000, 11500)).toBe(35);
        expect(secondsLeft(1000, 100000)).toBe(0);
    });
});

describe('operationView', () => {
    const address = 'http://mlsc.local:8080';

    it('shows the countdown while the change is pending', () => {
        const view = operationView({ state: 'pending', error: null }, 30, address);

        expect(view.level).toBe('info');
        expect(view.text).toContain('30 s');
        expect(view.text).toContain(address);
    });

    it('tells the user to rejoin the home Wi-Fi after a confirmed change', () => {
        const view = operationView({ state: 'confirmed', error: null }, 0, address);

        expect(view.level).toBe('success');
        expect(view.text).toContain('rejoin your home Wi-Fi');
        expect(view.text).toContain(address);
    });

    it('says the change was rolled back and why', () => {
        const view = operationView({ state: 'rolled_back', error: 'The change did not result in a connection.' }, 0, address);

        expect(view.level).toBe('warning');
        expect(view.text).toContain('rolled back');
        expect(view.text).toContain('The change did not result in a connection.');
    });

    it('shows a failed change as an error', () => {
        const view = operationView({ state: 'failed', error: 'Replaced by a newer Wi-Fi change.' }, 0, address);

        expect(view.level).toBe('danger');
        expect(view.text).toContain('Replaced by a newer Wi-Fi change.');
    });
});

describe('signalLabel', () => {
    it.each([[80, 'Strong'], [50, 'Good'], [30, 'Weak'], [5, 'Very weak']])('names %i as %s', (signal, label) => {
        expect(signalLabel(signal)).toBe(label);
    });
});
