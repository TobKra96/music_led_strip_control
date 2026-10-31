/** What the Gradients & Colours page shows and allows. Pure functions, so the page script only has to draw the result. */

export const GRADIENT = 'gradient';
export const COLOUR = 'colour';

export const MIN_STOPS = 2;
export const MAX_STOPS = 16;
export const MAX_NAME_LENGTH = 32;

/** Collection path below `/api/v2`, and the words of the page, per kind. */
export const KINDS = {
    [GRADIENT]: { path: '/gradients', singular: 'gradient', plural: 'Gradients', field: 'stops' },
    [COLOUR]: { path: '/colors', singular: 'colour', plural: 'Colours', field: 'rgb' },
};

/** URL of one entry; the name is the id, so it is encoded. */
export const entryPath = (kind, name) => `${KINDS[kind].path}/${encodeURIComponent(name)}`;

/**
 * The stops of an entry as the editor holds them: a colour is a list of one.
 * @param {string} kind
 * @param {{stops?: number[][], rgb?: number[]}} entry An entry of the API.
 * @return {number[][]}
 */
export const stopsOf = (kind, entry) => (kind === COLOUR ? [[...entry.rgb]] : entry.stops.map(stop => [...stop]));

/** The body to send for the given stops: `{stops}` for a gradient, `{rgb}` for a colour. */
export const payloadOf = (kind, name, stops) => (
    kind === COLOUR ? { name, rgb: stops[0] } : { name, stops }
);

export const rgbCss = ([r, g, b]) => `rgb(${r}, ${g}, ${b})`;

/** CSS background of the preview bar: stops are spread evenly, a single stop is a flat colour. */
export const previewCss = (stops) => (
    stops.length === 1 ? rgbCss(stops[0]) : `linear-gradient(90deg, ${stops.map(rgbCss).join(', ')})`
);

/** A new stop repeats the last one, so the preview does not change until it is picked. Full lists are returned as they are. */
export const addStop = (stops) => (
    stops.length >= MAX_STOPS ? stops : [...stops, [...(stops[stops.length - 1] ?? [255, 255, 255])]]
);

/** Stops without the one at `index`. Never goes below the minimum. */
export const removeStop = (stops, index) => (
    stops.length <= MIN_STOPS || !stops[index] ? stops : stops.filter((_, i) => i !== index)
);

/** Swap the stop at `index` with its neighbour `offset` places away (`-1` up, `1` down); out of range is a no-op. */
export const moveStop = (stops, index, offset) => {
    const target = index + offset;
    if (!stops[index] || !stops[target]) return stops;
    const moved = [...stops];
    [moved[index], moved[target]] = [moved[target], moved[index]];
    return moved;
};

export const setStop = (stops, index, rgb) => stops.map((stop, i) => (i === index ? [...rgb] : stop));

const sameStops = (a, b) => a.length === b.length && a.every((stop, i) => stop.every((channel, c) => channel === b[i][c]));

/** Readable effect name: "effect_beat_slide" -> "Beat Slide". */
const effectLabel = effect => effect.replace(/^effect_/, '').split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

/**
 * One Usage as a line of text.
 * @param {{target: string, effect: string, setting: string}} usage
 * @param {Object.<string, string>} [targetNames] Names of the devices by id; an unknown id is shown as it is.
 */
export const usageText = (usage, targetNames = {}) => (
    `${targetNames[usage.target] ?? usage.target}: ${effectLabel(usage.effect)}, ${usage.setting}`
);

/**
 * The state of the editor.
 * @param {object} state
 * @param {string} state.kind
 * @param {{name: string, predefined: boolean}|null} state.entry The saved entry; `null` for one that was not saved yet.
 * @param {string} state.name Name in the form.
 * @param {number[][]} state.stops Stops in the form.
 * @param {number[][]|null} state.savedStops Stops of the saved entry.
 * @param {Array|null} state.usages Where the saved entry is used; `null` while unknown.
 * @param {boolean} [state.busy] A request is running.
 */
export const editorView = ({ kind, entry, name, stops, savedStops, usages, busy = false }) => {
    const isNew = entry === null;
    const readOnly = !isNew && entry.predefined;
    const single = kind === COLOUR;
    const used = (usages ?? []).length > 0;
    const trimmed = name.trim();
    const dirty = isNew || trimmed !== entry.name || !sameStops(stops, savedStops);
    const validName = trimmed.length > 0 && trimmed.length <= MAX_NAME_LENGTH;

    return {
        isNew,
        readOnly,
        badge: readOnly ? 'Predefined' : null,
        notice: readOnly ? 'Predefined, read-only. Duplicate it to make an editable copy.' : null,
        title: isNew ? `New ${KINDS[kind].singular}` : entry.name,
        canEditName: !readOnly,
        canEditStops: !readOnly,
        showStopTools: !readOnly && !single,
        canAddStop: !readOnly && !single && stops.length < MAX_STOPS,
        canRemoveStop: !readOnly && !single && stops.length > MIN_STOPS,
        canSave: !busy && !readOnly && dirty && validName,
        canDuplicate: !busy && !isNew,
        canDelete: !busy && !isNew && !readOnly && !used,
        deleteHint: used ? deleteBlockedMessage(entry.name, usages) : null,
        // Saving restarts every Device that uses the entry, so say where it is used before saving.
        saveWarning: !isNew && !readOnly && dirty && used
            ? `Saving restarts the devices that use "${entry.name}".` : null,
        showUsages: !isNew && used,
        preview: previewCss(stops),
    };
};

/**
 * The message that says why an entry cannot be deleted.
 * @param {string} name
 * @param {Array<{target: string, effect: string, setting: string}>} usages
 * @param {Object.<string, string>} [targetNames]
 */
export const deleteBlockedMessage = (name, usages, targetNames = {}) => (
    `Cannot delete "${name}": it is used by ${usages.map(u => usageText(u, targetNames)).join('; ')}. Switch those settings to another entry first.`
);

/** Label of the option that stands for a name that no longer exists. */
export const missingLabel = name => `missing: ${name}`;

/**
 * Whether a stored setting value names an entry that does not exist (a Missing Reference). Case-insensitive, like the names.
 * @param {string|null|undefined} value
 * @param {string[]} names All current names of that kind.
 */
export const isMissingReference = (value, names) => (
    typeof value === 'string' && value !== '' && !names.some(n => n.toLowerCase() === value.toLowerCase())
);

/** `rgb(r, g, b)` or `rgba(r, g, b, a)` text of the picker as `[r, g, b]` clamped to 0-255; the opacity is dropped. */
export const parseRgbText = (text) => {
    const channels = (text.match(/\d+/g) ?? []).slice(0, 3).map(Number);
    return channels.length === 3 ? channels.map(c => Math.min(255, c)) : null;
};
