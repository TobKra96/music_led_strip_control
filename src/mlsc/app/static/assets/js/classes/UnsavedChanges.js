const IGNORED_TYPES = ['file', 'hidden', 'button', 'submit', 'reset', 'image'];

/**
 * Tells whether a settings form differs from the values it had when it was last marked clean.
 * The form is walked generically, so reverting an edit clears the dirty state again.
 */
export default class UnsavedChanges {
    /**
     * @param {HTMLFormElement} form The form to watch, e.g. `#settingsForm`.
     */
    constructor(form) {
        this.form = form;
        this.baseline = null;
        window.addEventListener('beforeunload', (event) => {
            if (this.isDirty()) {
                event.preventDefault();
                event.returnValue = '';
            }
        });
    }

    /**
     * Take the current form values as the saved state. Call after the page is populated and after each successful save.
     */
    markClean() {
        this.baseline = this.snapshot();
    }

    /**
     * @return {boolean} True if the form changed since the last `markClean()`. Never true before the first one.
     */
    isDirty() {
        return this.baseline !== null && this.snapshot() !== this.baseline;
    }

    /**
     * Ask before discarding changes.
     * @return {boolean} True if it is fine to leave: nothing is dirty, or the user confirmed.
     */
    guard() {
        return !this.isDirty() || window.confirm('Discard unsaved changes?');
    }

    /**
     * @return {string} The relevant control values, serialised in a stable order.
     */
    snapshot() {
        const state = {};
        for (const control of this.form.elements) {
            if (control.disabled || IGNORED_TYPES.includes(control.type) || control.closest('[data-unsaved-ignore]')) {
                continue;
            }
            const toggle = control.type === 'checkbox' || control.type === 'radio';
            const key = control.id || (control.name && toggle ? `${control.name}:${control.value}` : control.name);
            if (!key) {
                continue;
            }
            if (toggle) {
                state[key] = control.checked;
            } else if (control.type === 'select-multiple') {
                state[key] = Array.from(control.selectedOptions, (option) => option.value);
            } else {
                state[key] = control.value;
            }
        }
        return JSON.stringify(Object.entries(state).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
    }
}
