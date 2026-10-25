import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import UnsavedChanges from '../../src/mlsc/app/static/assets/js/classes/UnsavedChanges.js';

let form;
let unloadHandlers;

beforeEach(() => {
    document.body.innerHTML = `
        <form id="settingsForm">
            <input id="name" type="text" value="strip">
            <input id="enabled" type="checkbox" checked>
            <select id="mode"><option value="a" selected>A</option><option value="b">B</option></select>
            <input id="secret" type="hidden" value="x">
            <input id="off" type="text" value="v" disabled>
            <input id="skip" type="text" value="v" data-unsaved-ignore>
            <input type="text" name="byName" value="n">
        </form>`;
    form = document.getElementById('settingsForm');
    unloadHandlers = [];
    const add = window.addEventListener.bind(window);
    vi.spyOn(window, 'addEventListener').mockImplementation((type, handler, options) => {
        if (type === 'beforeunload') unloadHandlers.push(handler);
        add(type, handler, options);
    });
});

afterEach(() => {
    unloadHandlers.forEach((handler) => window.removeEventListener('beforeunload', handler));
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

const edit = (id, value) => {
    document.getElementById(id).value = value;
};

it('is never dirty before the first markClean', () => {
    const unsaved = new UnsavedChanges(form);
    edit('name', 'changed');
    expect(unsaved.isDirty()).toBe(false);
});

it('is clean right after markClean', () => {
    const unsaved = new UnsavedChanges(form);
    unsaved.markClean();
    expect(unsaved.isDirty()).toBe(false);
});

it('detects edited text, checkbox, select and name-keyed fields', () => {
    const unsaved = new UnsavedChanges(form);
    unsaved.markClean();

    edit('name', 'changed');
    expect(unsaved.isDirty()).toBe(true);
    edit('name', 'strip');
    expect(unsaved.isDirty()).toBe(false);

    document.getElementById('enabled').checked = false;
    expect(unsaved.isDirty()).toBe(true);
    document.getElementById('enabled').checked = true;

    edit('mode', 'b');
    expect(unsaved.isDirty()).toBe(true);
    edit('mode', 'a');

    form.elements.byName.value = 'other';
    expect(unsaved.isDirty()).toBe(true);
});

it('ignores hidden, disabled and data-unsaved-ignore controls', () => {
    const unsaved = new UnsavedChanges(form);
    unsaved.markClean();
    edit('secret', 'y');
    edit('off', 'w');
    edit('skip', 'w');
    expect(unsaved.isDirty()).toBe(false);
});

it('re-baselines on markClean', () => {
    const unsaved = new UnsavedChanges(form);
    unsaved.markClean();
    edit('name', 'changed');
    unsaved.markClean();
    expect(unsaved.isDirty()).toBe(false);
});

it('only prevents unload when dirty', () => {
    const unsaved = new UnsavedChanges(form);
    unsaved.markClean();

    const clean = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(clean);
    expect(clean.defaultPrevented).toBe(false);

    edit('name', 'changed');
    const dirty = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(dirty);
    expect(dirty.defaultPrevented).toBe(true);
});

it('guard confirms only when dirty', () => {
    const confirm = vi.fn(() => false);
    vi.stubGlobal('confirm', confirm);
    const unsaved = new UnsavedChanges(form);
    unsaved.markClean();

    expect(unsaved.guard()).toBe(true);
    expect(confirm).not.toHaveBeenCalled();

    edit('name', 'changed');
    expect(unsaved.guard()).toBe(false);
    expect(confirm).toHaveBeenCalledWith('Discard unsaved changes?');

    confirm.mockReturnValue(true);
    expect(unsaved.guard()).toBe(true);
});
