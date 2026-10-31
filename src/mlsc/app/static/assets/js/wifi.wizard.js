import { api } from './classes/Api.js';
import WifiWizard from './classes/WifiWizard.js';
import { shouldAutoOpen } from './classes/WifiView.js';

const DISMISSED_KEY = 'wifiWizardDismissed';

const readDismissed = () => {
    try {
        return sessionStorage.getItem(DISMISSED_KEY) === '1';
    } catch {
        return false;
    }
};

const writeDismissed = () => {
    try {
        sessionStorage.setItem(DISMISSED_KEY, '1');
    } catch {
        // Without storage the wizard opens again on the next page, which is harmless.
    }
};

const wizard = new WifiWizard({ onClosed: (leftEarly) => { if (leftEarly) writeDismissed(); } });

/** Open the wizard on request, for the Wi-Fi Settings page. */
export const openWifiWizard = () => api.get('/wifi/status').then(status => wizard.open(status));

// The wizard opens by itself for a user who reached the Pi over its Hotspot.
api.get('/wifi/status').then((status) => {
    if (shouldAutoOpen(status, readDismissed())) wizard.open(status);
}).catch(() => {});

$('#wifi_wizard_btn').on('click', () => openWifiWizard().catch(() => {}));
