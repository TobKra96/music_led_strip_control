import { api } from './classes/Api.js';
import Banner from './classes/Banner.js';
import { events } from './classes/Events.js';

// Shown only when the stream stays down for a moment, so reloading or leaving the page does not flash it.
const DISCONNECT_GRACE_MS = 3000;

const connectionBanner = new Banner('connection');
let disconnectTimer = null;

events.on('disconnected', () => {
    if (disconnectTimer) return;
    disconnectTimer = setTimeout(() => {
        connectionBanner.show({
            level: 'warning',
            title: 'Connection lost',
            message: 'The page does not receive live updates. Trying to reconnect…',
        });
    }, DISCONNECT_GRACE_MS);
});

events.on('ready', () => {
    clearTimeout(disconnectTimer);
    disconnectTimer = null;
    connectionBanner.hide();
});

/**
 * A Diagnosis is `{device_id, status, message, suggested_fix}`. Anything but `ok` keeps a banner up for that device.
 * @param {{device_id: string, status: string, message: string, suggested_fix: string | null}} diagnosis
 */
events.on('diagnosis', (diagnosis) => {
    const banner = new Banner(`diagnosis-${diagnosis.device_id}`);
    if (diagnosis.status === 'ok') {
        banner.hide();
        return;
    }
    banner.show({
        level: diagnosis.status === 'warning' ? 'warning' : 'error',
        title: `Problem with ${diagnosis.device_id}`,
        message: diagnosis.suggested_fix ? `${diagnosis.message} ${diagnosis.suggested_fix}` : diagnosis.message,
    });
});

/** Show the Migration Report of a Config Migration once, until the user dismisses it. */
const showMigrationReport = async () => {
    let report;
    try {
        report = await api.get('/system/migration-report');
    } catch {
        return;  // No report to show (`404`), or the server cannot be reached.
    }

    const warnings = report.entries.filter(entry => entry.level === 'warning');
    const upgraded = `Your configuration was upgraded from version ${report.from_version} to ${report.to_version}.`;
    const message = warnings.length
        ? `${upgraded} ${warnings.length} value${warnings.length === 1 ? '' : 's'} could not be carried over exactly.`
        : upgraded;

    new Banner('migration-report').show({
        level: warnings.length ? 'warning' : 'info',
        title: 'Configuration upgraded',
        message,
        details: report.entries.map(entry => `${entry.path}: ${entry.message}`),
        onDismiss: () => api.delete('/system/migration-report').catch(() => {}),
    });
};

$(() => {
    events.connect();
    showMigrationReport();
});
