import { describe, expect, it } from 'vitest';
import { ROLLBACK_SECONDS, addressOf, operationView, pageView, secondsLeft, signalLabel, signalLevel, hotspotProblem, connectProblem } from '../../src/mlsc/app/static/assets/js/classes/WifiView.js';

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
        const view = pageView({ ...ready, mode: 'hotspot', connected: false, ssid: null, ip: '10.42.0.1', hotspot: { ssid: 'MLSC-1234', password: 'abcd1234', address: '10.42.0.1' } }, session);

        expect(view.summary).toBe('Hotspot MLSC-1234 is on, IP address 10.42.0.1.');
        expect(view.hotspot).toEqual({ ssid: 'MLSC-1234', password: 'abcd1234', address: '10.42.0.1' });
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

describe('signalLevel', () => {
    it.each([[100, 4], [80, 4], [70, 3], [50, 2], [45, 2], [30, 1], [20, 1], [10, 0], [0, 0]])('turns %i into %i of 4 bars', (signal, level) => {
        expect(signalLevel(signal)).toBe(level);
    });

    it('agrees with the label: a network with no bars is Very weak', () => {
        expect(signalLabel(10)).toBe('Very weak');
    });
});

describe('hotspotProblem', () => {
    it('accepts empty fields, which the server fills in', () => {
        expect(hotspotProblem('', '')).toBeNull();
    });

    it('accepts a name and a password of 8 to 63 characters', () => {
        expect(hotspotProblem('My Hotspot', '12345678')).toBeNull();
        expect(hotspotProblem('', 'x'.repeat(63))).toBeNull();
    });

    it('rejects a password shorter than 8 characters before it is sent', () => {
        expect(hotspotProblem('', '1234567')).toBe('The Hotspot password needs at least 8 characters.');
    });

    it('rejects a password longer than 63 characters and a name longer than 32', () => {
        expect(hotspotProblem('', 'x'.repeat(64))).toBe('The Hotspot password can have at most 63 characters.');
        expect(hotspotProblem('n'.repeat(33), '')).toBe('The Hotspot name can have at most 32 characters.');
    });
});

describe('hotspotProblem with an address', () => {
    it.each(['10.1.2.3', '172.16.0.1', '172.31.5.9', '192.168.50.1'])('accepts the private address %s', (ip) => {
        expect(hotspotProblem('', '', ip)).toBeNull();
    });

    it.each(['192.168.1', 'abc', '1.2.3.4.5', '192.168.1.300', '192.168.1.1/24', '192.168.050.1'])('rejects %s as not an IPv4 address', (ip) => {
        expect(hotspotProblem('', '', ip)).toBe('The Hotspot address must be an IPv4 address such as 192.168.50.1.');
    });

    it.each(['8.8.8.8', '172.32.0.1', '172.15.0.1', '192.169.0.1'])('rejects the public address %s', (ip) => {
        expect(hotspotProblem('', '', ip)).toContain('must be a private address');
    });

    it.each(['192.168.50.0', '192.168.50.255'])('rejects the network or broadcast address %s', (ip) => {
        expect(hotspotProblem('', '', ip)).toContain('network and broadcast');
    });
});

describe('connectProblem', () => {
    const networks = [
        { ssid: 'Home', security: 'WPA2', known: false },
        { ssid: 'Saved', security: 'WPA2', known: true },
        { ssid: 'Cafe', security: null, known: false },
    ];

    it('asks for a name first', () => {
        expect(connectProblem('', '', networks)).toBe('Enter or pick a network name first.');
    });

    it('asks for the password of a secured network that is not saved', () => {
        expect(connectProblem('Home', '', networks)).toBe('Enter the password for Home.');
    });

    it('lets a saved network, an open network and one with a password through', () => {
        expect(connectProblem('Saved', '', networks)).toBeNull();
        expect(connectProblem('Cafe', '', networks)).toBeNull();
        expect(connectProblem('Home', 'secret123', networks)).toBeNull();
    });

    it('lets a name that was not scanned through, such as a hidden network', () => {
        expect(connectProblem('Hidden', '', networks)).toBeNull();
    });

    it('rejects a password outside 8 to 63 characters for a secured network', () => {
        expect(connectProblem('Home', 'short', networks)).toBe('A Wi-Fi password has 8 to 63 characters.');
    });
});
