import Tagin from '../../plugins/tagin/js/tagin.js';
import EffectManager from './EffectManager.js';
const effectManager = new EffectManager();

// Do not init tagin if it is not on the page.
const taginEl = document.querySelector('.tagin');
const tagin = taginEl ? new Tagin(taginEl) : null;


// classes/Device.js
class Device {
    /** Create a device object. */
    constructor(/** @type {DeviceParams} */ params) {
        this.assigned_to = params.assigned_to;
        /** @type {string} */
        this.id = params.id;
        /** @private */
        this._name = params.name;

        this.isGroup = this.id.startsWith('group_') || this.id === 'all_devices';
        /** @type {HTMLAnchorElement} */
        this.link = $(`a[data-device-id=${this.id}`).get(0);

        // Insert first device ('all_devices' or 'device_0') into localStorage if 'lastDevice' does not exist yet.
        !('lastDevice' in localStorage) && localStorage.setItem('lastDevice', this.id);

        // Select last selected device if there is any.
        this.isCurrent && (
            this._activate(),
            $(`a[data-device-id=${this.id}`).tab('show'),
            // Async function. Only get active effect on the dashboard page.
            ['', 'dashboard'].includes(window.location.pathname.split('/').pop()) ? this.getActiveEffect() : null
        );

        // Add basic behavior to pills.
        $(`a[data-device-id=${this.id}`).on('click', e => {
            this.link = e.currentTarget;
            this._activate();
        });
    }

    /**
     * Set active device in device bar and save it to localStorage.
     */
    _activate() {
        const deviceIconEl = $('#device_type_icon');
        if (this.isGroup) {
            deviceIconEl.removeClass('fa-regular fa-lightbulb');
            deviceIconEl.addClass('fa-solid fa-circle-nodes');
        } else {
            deviceIconEl.addClass('fa-regular fa-lightbulb');
            deviceIconEl.removeClass('fa-solid fa-circle-nodes');
        }
        $('#selected_device_txt').text(this.name);
        localStorage.setItem('lastDevice', this.id);
        effectManager.currentDevice = this;
    }

    /**
     * Getter to check if the selected device  matches `lastDevice` in the localStorage.
     * @return {boolean}
     */
    get isCurrent() {
        return this.id === localStorage.getItem('lastDevice');
    }

    /** @return {string} */
    get name() {
        return this._name;
    }

    /** @param {string} name */
    set name(name) {
        this._name = name;
        // Update HTML elements on name change.
        if (this.link && this.link !== '') {
            this.link.innerHTML = name;
        }
    }

    /**
     * Create a device pill Element and return it.
     * @param {string} currentDeviceId If the device is the current device, add the `active` class.
     * @return {HTMLAnchorElement}
     */
    createPill(currentDeviceId) {
        const link = document.createElement('a');
        const active = currentDeviceId === this.id ? 'active' : '';
        link.innerHTML = this.name;
        link.href = `#pills-${this.id}`;
        link.classList = `nav-link ${active}`;
        link.setAttribute('data-device-id', this.id);
        link.role = 'tab';
        link.setAttribute('data-toggle', 'pill');
        link.setAttribute('aria-controls', `pills-${this.id}`);
        link.setAttribute('aria-selected', 'false');
        this.link = link;
        return link;
    }

    /**
     * Call API to get all device settings.
     * @param {string} excludedKey
     * @return {Promise.<jQuery.jqXHR>}
     */
    async getSettings(excludedKey = '') {
        const settings = { device: this.id };
        excludedKey !== '' && (settings.excluded_key = excludedKey);
        return await $.ajax({
            url: '/api/settings/device',
            data: settings
        });
    }

    /**
     * Call API to get all device output settings.
     * @return {Promise.<jQuery.jqXHR>}
     */
    async getOutputSettings() {
        return await $.ajax({
            url: '/api/settings/device/output-type',
            data: { device: this.id }
        });
    }

    /**
     * Call API to get all effect settings.
     * @param {string} effectId
     * @return {Promise.<jQuery.jqXHR>}
     */
    async getEffectSettings(effectId) {
        return await $.ajax({
            url: '/api/settings/effect',
            data: {
                device: this.id,
                effect: effectId
            }
        });
    }

    /**
     * Call API to get the `Random Cycle` effect status.
     * @return {Promise.<jQuery.jqXHR>}
     */
    async getCycleStatus() {
        return await $.ajax({
            url: '/api/effect/cycle-status',
            data: { device: this.id }
        });
    }

    /**
     * Set border style for `Random Cycle` button.
     */
    setCycleStatusStyle() {
        this.getCycleStatus().then((response) => {
            // TODO: Implement UI/UX for multiple devices with active `Random Cycle`.
            if (response.random_cycle_active) {
                $('#effect_random_cycle').addClass('active');
            } else {
                $('#effect_random_cycle').removeClass('active');
            }
        });
    }

    /**
     * Show indicator dot on effect buttons which are active.
     * @param {Array.<{device: string, effect: string}>} devicesFromApi List of devices with active effects.
     */
    setDeviceIndicators(devicesFromApi) {
        // Group devices by effect.
        const result = devicesFromApi.reduce((group, device) => {
            const { effect } = device;
            group[effect] = group[effect] ?? [];
            group[effect].push(device);
            return group;
        }, {});

        // Insert device names into active indicator title.
        $.ajax('/api/system/devices').done((refreshedDevices) => {
            $('.active_indicator').addClass('d-none');
            Object.entries(result).forEach(([effect, devices]) => {
                let grouped = [];
                Object.values(devices).forEach((item) => {
                    const deviceName = refreshedDevices.find(d => d.id === item.device).name;
                    grouped.push(deviceName);
                });
                // TODO: Clicking the dot should show a list of devices with that effect.
                // Currently only shows devices on hover in a title.
                $(`#${effect}`).siblings('.active_indicator').removeClass('d-none').attr('title', grouped.join(', '));
            });
        });
    }

    /**
     * Call API to get the active effect for a device.
     */
    getActiveEffect() {
        $.ajax('/api/effect/active').done(data => {
            this.setCycleStatusStyle();

            let effects;
            if (this.id === 'all_devices') {  // `all_devices` is a group, but it's not returned from the API.
                effects = data.devices.map(x => x.effect);
            } else {
                const group = data.groups.find(x => x.group === this.id);
                effects = group ? group.effects : [data.devices.find(x => x.device === this.id).effect];
            }
            this.setActiveEffectStyle(effects);
        });

        // WIP: Not working yet.
        // Does not update indicator dot on effect click.
        // this.setDeviceIndicators(data.devices);
    }


    /**
     * Set style for active effect buttons and update device bar data.
     * @param {Array.<string>} newActiveEffects Array of effects.
     */
    setActiveEffectStyle(newActiveEffects) {
        $('.dashboard_effect_active').removeClass('dashboard_effect_active');

        const uniqueEffects = [...new Set(newActiveEffects)];

        const effectIconEl = $('#effect_icon');
        const effectNameEl = $('#selected_effect_txt');
        effectIconEl.removeClass();

        if (uniqueEffects.length === 1) {
            const effectIcon = $(`#${uniqueEffects[0]} i`).attr('class');
            const effectName = $(`#${uniqueEffects[0]}`).text().trim();
            effectIconEl.addClass(effectIcon);
            effectNameEl.text(effectName);
        } else {
            effectIconEl.addClass("fa-solid fa-bolt-lightning");
            effectNameEl.text('Multiple Effects');
        }

        uniqueEffects.forEach((effect) => {
            $(`#${effect}`).addClass('dashboard_effect_active');
        });
    }

    /**
     * Populate device settings forms with data from config.
     */
    refreshConfig() {
        this.getSettings('effects').then((response) => {
            $.each(response.settings, (key, value) => {
                const el = $(`#${key}`);
                if (el.is(':checkbox')) {
                    el.prop('checked', value);
                } else if (el.is("[type='range']")) {
                    el.val(value);
                    $(`span[for='${key}']`).text(value);
                } else if (el.is("[type='option']")) {
                    _populateDeviceGroups(value);
                    _populateGlobalGroups(Object.values(value));
                } else {
                    el.val(value);
                }
                el.trigger('change');
            });
        });

        this.getOutputSettings().then((response) => {
            $.each(response.output_settings, (key, value) => {
                const el = $(`#${key}`);
                if (el.is(':checkbox')) {
                    el.prop('checked', value);
                } else {
                    el.val(value);
                }
                el.trigger('change');
            });
        });
    }

}

/**
 * Populate selected device groups on Device Settings page.
 * @param {Object} deviceGroups
 */
const _populateDeviceGroups = (deviceGroups) => {
    tagin.clearTags();
    tagin.addTag(deviceGroups);
}

/**
 * Populate global device groups dropdown on Device Settings page.
 * @param {Array.<string>} deviceGroups
 */
const _populateGlobalGroups = (deviceGroups) => {
    const dropdown = $('#device_group_dropdown');

    // Clear all dropdown group options.
    dropdown.empty();

    // Populate device group dropdown with all available groups.
    $.each(jinja_groups.groups, (groupId, globalGroup) => {
        const dropdownItem = $(`<option tag-id="${groupId}" value="${globalGroup}">${globalGroup}</option>`)
        dropdown.append(dropdownItem);

        if (deviceGroups.includes(globalGroup)) {
            dropdownItem.hide();
        }
    });

    // Add placeholder option on top.
    dropdown.prepend('<option value="placeholder" disabled selected>Select a group</option>');
    dropdown.get(0).selectedIndex = 0;
}

export { Device, tagin };


/**
 * @typedef {object} DeviceParams
 * @property {Object.<string, string>} assigned_to
 * @property {string} id
 * @property {string} name
 */
