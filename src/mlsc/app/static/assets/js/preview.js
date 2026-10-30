import { Device } from './classes/Device.js';
import Toast from './classes/Toast.js';
import StripPreview from './classes/StripPreview.js';


$(() => {
    // Allow to scroll sidebar when page is reloaded and mouse is already on top of sidebar.
    $('.navbar-content').trigger('mouseover');

    if (!jinja_devices.length) {
        new Toast('No devices found. Create a new device in "Device Settings".', true).info();
        return;
    }

    // Create Base Group ('all_devices').
    const devicesById = Object.fromEntries(jinja_devices.map(device => [device.id, device.name]));
    const baseGroup = new Device({ assigned_to: devicesById, id: 'all_devices', name: 'All Devices' });
    const devices = jinja_devices.map(d => new Device(d));
    const groups = [baseGroup, ...jinja_groups.map(g => new Device(g))];

    const status = document.getElementById('strip-preview-status');
    const preview = new StripPreview(document.getElementById('strip-preview'), count => {
        status.textContent = `${count} LEDs`;
    });
    // A group or `all_devices` shows its first device.
    const show = item => preview.show(item.isGroup ? Object.keys(item.assigned_to)[0] : item.id);

    const items = [...devices, ...groups];
    const current = items.find(item => item.isCurrent) ?? devices[0];
    current && show(current);
    items.forEach(item => $(item.link).on('click', () => show(item)));
    window.addEventListener('pagehide', () => preview.stop());
});
