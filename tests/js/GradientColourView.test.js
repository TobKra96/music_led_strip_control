import { describe, expect, it } from 'vitest';
import {
    COLOUR, GRADIENT, MAX_STOPS, addStop, deleteBlockedMessage, editorView, entryPath, isMissingReference, missingLabel,
    moveStop, parseRgbText, payloadOf, previewCss, removeStop, setStop, stopsOf, usageText,
} from '../../src/mlsc/app/static/assets/js/classes/GradientColourView.js';

const RED = [255, 0, 0];
const GREEN = [0, 255, 0];
const BLUE = [0, 0, 255];

const custom = { name: 'My Party', stops: [RED, GREEN], predefined: false };
const predefined = { name: 'Spectral', stops: [RED, GREEN, BLUE], predefined: true };
const usage = { target: 'device_0', effect: 'effect_beat_slide', setting: 'gradient' };

const view = (overrides = {}) => editorView({
    kind: GRADIENT, entry: custom, name: custom.name, stops: custom.stops, savedStops: custom.stops, usages: [], ...overrides,
});

describe('stop list', () => {
    it('adds a stop that repeats the last one', () => {
        expect(addStop([RED, GREEN])).toEqual([RED, GREEN, GREEN]);
    });

    it('does not add past the maximum', () => {
        const full = Array.from({ length: MAX_STOPS }, () => RED);
        expect(addStop(full)).toBe(full);
    });

    it('removes a stop but never goes below two', () => {
        expect(removeStop([RED, GREEN, BLUE], 1)).toEqual([RED, BLUE]);
        const two = [RED, GREEN];
        expect(removeStop(two, 0)).toBe(two);
    });

    it('reorders a stop up and down', () => {
        expect(moveStop([RED, GREEN, BLUE], 2, -1)).toEqual([RED, BLUE, GREEN]);
        expect(moveStop([RED, GREEN, BLUE], 0, 1)).toEqual([GREEN, RED, BLUE]);
    });

    it('ignores moves off either end', () => {
        const stops = [RED, GREEN];
        expect(moveStop(stops, 0, -1)).toBe(stops);
        expect(moveStop(stops, 1, 1)).toBe(stops);
    });

    it('sets one stop without touching the others or the original', () => {
        const stops = [RED, GREEN];
        expect(setStop(stops, 1, BLUE)).toEqual([RED, BLUE]);
        expect(stops).toEqual([RED, GREEN]);
    });
});

describe('preview bar', () => {
    it('spreads gradient stops evenly', () => {
        expect(previewCss([RED, GREEN, BLUE])).toBe('linear-gradient(90deg, rgb(255, 0, 0), rgb(0, 255, 0), rgb(0, 0, 255))');
    });

    it('is a flat colour for a single stop', () => {
        expect(previewCss([BLUE])).toBe('rgb(0, 0, 255)');
    });

    it('follows the edited stops', () => {
        expect(view({ stops: [RED, BLUE] }).preview).toContain('rgb(0, 0, 255)');
    });
});

describe('API mapping', () => {
    it('encodes the name in the address', () => {
        expect(entryPath(GRADIENT, 'My Party/ü')).toBe('/gradients/My%20Party%2F%C3%BC');
        expect(entryPath(COLOUR, 'Teal')).toBe('/colors/Teal');
    });

    it('holds a colour as a list of one stop and sends it back as rgb', () => {
        expect(stopsOf(COLOUR, { name: 'Teal', rgb: [0, 128, 128] })).toEqual([[0, 128, 128]]);
        expect(payloadOf(COLOUR, 'Teal', [[0, 128, 128]])).toEqual({ name: 'Teal', rgb: [0, 128, 128] });
        expect(payloadOf(GRADIENT, 'X', [RED, BLUE])).toEqual({ name: 'X', stops: [RED, BLUE] });
    });
});

describe('editor states', () => {
    it('lets a custom entry be edited, but saves only a change', () => {
        expect(view()).toMatchObject({ readOnly: false, canSave: false, canDuplicate: true, canDelete: true, badge: null });
        expect(view({ name: 'Renamed' }).canSave).toBe(true);
        expect(view({ stops: [RED, BLUE] }).canSave).toBe(true);
    });

    it('does not save an empty or too long name', () => {
        expect(view({ name: '   ' }).canSave).toBe(false);
        expect(view({ name: 'x'.repeat(33) }).canSave).toBe(false);
    });

    it('shows a predefined entry read-only with Duplicate enabled', () => {
        const v = view({ entry: predefined, name: 'Spectral', stops: predefined.stops, savedStops: predefined.stops });
        expect(v).toMatchObject({
            readOnly: true, badge: 'Predefined', canEditName: false, canEditStops: false, showStopTools: false,
            canSave: false, canDelete: false, canDuplicate: true,
        });
    });

    it('offers a new entry only to save', () => {
        expect(view({ entry: null, name: 'Fresh', savedStops: null })).toMatchObject({ canSave: true, canDuplicate: false, canDelete: false });
    });

    it('limits the stop buttons to the minimum and maximum', () => {
        expect(view().canRemoveStop).toBe(false);
        expect(view({ stops: [RED, GREEN, BLUE] }).canRemoveStop).toBe(true);
        expect(view({ stops: Array.from({ length: MAX_STOPS }, () => RED) }).canAddStop).toBe(false);
    });

    it('edits a colour with a single picker and no stop tools', () => {
        const v = editorView({
            kind: COLOUR, entry: { name: 'Teal', rgb: [0, 128, 128], predefined: false }, name: 'Teal',
            stops: [[0, 128, 128]], savedStops: [[0, 128, 128]], usages: [],
        });
        expect(v).toMatchObject({ showStopTools: false, canAddStop: false, canRemoveStop: false, canEditStops: true });
    });

    it('keeps every action off while a request runs', () => {
        expect(view({ name: 'Renamed', busy: true })).toMatchObject({ canSave: false, canDuplicate: false, canDelete: false });
    });
});

describe('entry in use', () => {
    it('disables Delete up front and says where it is used', () => {
        const v = view({ usages: [usage] });
        expect(v.canDelete).toBe(false);
        expect(v.showUsages).toBe(true);
        expect(v.deleteHint).toBe('Cannot delete "My Party": it is used by device_0: Beat Slide, gradient. Switch those settings to another entry first.');
    });

    it('warns about the restart before an in-use entry is saved', () => {
        expect(view({ usages: [usage], name: 'Renamed' }).saveWarning).toBe('Saving restarts the devices that use "My Party".');
        expect(view({ usages: [usage] }).saveWarning).toBeNull();
        expect(view({ name: 'Renamed' }).saveWarning).toBeNull();
    });

    it('names devices when their names are known', () => {
        expect(usageText(usage, { device_0: 'Desk' })).toBe('Desk: Beat Slide, gradient');
        expect(deleteBlockedMessage('X', [usage, { ...usage, target: 'device_1' }], { device_1: 'Shelf' }))
            .toContain('device_0: Beat Slide, gradient; Shelf: Beat Slide, gradient');
    });
});

describe('missing reference', () => {
    it('flags a name that is not among the current ones, ignoring case', () => {
        expect(isMissingReference('gone', ['red', 'blue'])).toBe(true);
        expect(isMissingReference('RED', ['red', 'blue'])).toBe(false);
        expect(isMissingReference('', ['red'])).toBe(false);
        expect(isMissingReference(undefined, ['red'])).toBe(false);
    });

    it('labels the flag', () => {
        expect(missingLabel('gone')).toBe('missing: gone');
    });
});

describe('parseRgbText', () => {
    it('reads the picker text and clamps the channels', () => {
        expect(parseRgbText('rgb(1, 2, 300)')).toEqual([1, 2, 255]);
        expect(parseRgbText('rgba(10, 20, 30, 0.5)')).toEqual([10, 20, 30]);
        expect(parseRgbText('nonsense')).toBeNull();
    });
});
