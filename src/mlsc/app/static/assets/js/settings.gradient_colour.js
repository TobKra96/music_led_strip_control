import { api } from './classes/Api.js';
import {
    COLOUR, GRADIENT, KINDS, addStop, deleteBlockedMessage, editorView, entryPath, moveStop, parseRgbText, payloadOf,
    previewCss, removeStop, rgbCss, setStop, stopsOf, usageText,
} from './classes/GradientColourView.js';
import { initPickr } from './classes/Pickr.js';
import Toast from './classes/Toast.js';

const targetNames = Object.fromEntries(jinja_devices.map(device => [device.id, device.name]));

let kind = GRADIENT;
/** The entries of each kind, as the API lists them. */
const entries = { [GRADIENT]: [], [COLOUR]: [] };
/** The saved entry being edited, or `null` for a new one. */
let entry = null;
/** What the form holds. `null` while nothing is open. */
let draft = null;
let usages = [];
let busy = false;

const entryStops = item => stopsOf(kind, item);

const open = (item) => {
    entry = item;
    draft = item ? { name: item.name, stops: entryStops(item) } : { name: '', stops: kind === COLOUR ? [[255, 255, 255]] : [[255, 0, 0], [0, 0, 255]] };
    usages = [];
    render();
    if (item) {
        const opened = item.name;
        api.get(`${entryPath(kind, opened)}/usages`).then((found) => {
            if (entry && entry.name === opened) {
                usages = found;
                renderActions();
            }
        }).catch(error => new Toast(`Could not load where "${opened}" is used. ${error.summary ?? error.message}`).error());
    }
};

const view = () => editorView({
    kind, entry, name: draft.name, stops: draft.stops, savedStops: entry ? entryStops(entry) : null, usages, busy,
});

const showMessage = (level, text) => $('#message').removeClass('d-none alert-success alert-danger alert-info').addClass(`alert-${level}`).text(text);

/** Buttons, hints and the preview: everything that follows the draft without rebuilding the stop pickers. */
const renderActions = () => {
    const v = view();
    $('#preview_bar').css('background', v.preview);
    $('#save_btn').prop('disabled', !v.canSave);
    $('#duplicate_btn').prop('disabled', !v.canDuplicate);
    $('#delete_btn').prop('disabled', !v.canDelete).attr('title', v.deleteHint ?? '');
    $('#save_warning').toggleClass('d-none', !v.saveWarning).text(v.saveWarning ?? '');
    $('#usages_box').toggleClass('d-none', !v.showUsages);
    $('#usages').empty().append(usages.map(usage => $('<li></li>').text(usageText(usage, targetNames))));
    $('#add_stop_btn').toggleClass('d-none', !v.showStopTools).prop('disabled', !v.canAddStop);
    $('.stop-remove').prop('disabled', !v.canRemoveStop);
    $('#entry_list .entry-item').each(function () {
        $(this).toggleClass('selected', entry !== null && $(this).attr('data-name') === entry.name);
    });
};

const renderStops = (v) => {
    const $stops = $('#stops').empty();
    draft.stops.forEach((stop, index) => {
        const $row = $('<div class="stop-row"></div>');
        if (v.canEditStops) {
            const $picker = $('<button type="button" class="stop-picker"></button>').attr('id', `stop_picker_${index}`).attr('aria-label', `Colour of stop ${index + 1}`);
            const $input = $('<input type="text" class="form-control stop-input" spellcheck="false">').attr('id', `stop_input_${index}`);
            $row.append($picker, $input);
        } else {
            $row.append($('<span class="stop-picker read-only"></span>').css('background', rgbCss(stop)), $('<code></code>').text(rgbCss(stop)));
        }
        if (v.showStopTools) {
            const button = (cls, label, text, action) => $(`<button type="button" class="btn btn-sm ${cls}"></button>`).attr('aria-label', label).text(text).on('click', action);
            $row.append(
                button('btn-outline-secondary', 'Move up', '↑', () => edit(moveStop(draft.stops, index, -1))).prop('disabled', index === 0),
                button('btn-outline-secondary', 'Move down', '↓', () => edit(moveStop(draft.stops, index, 1))).prop('disabled', index === draft.stops.length - 1),
                button('btn-outline-danger stop-remove', 'Remove stop', '✕', () => edit(removeStop(draft.stops, index))),
            );
        }
        $stops.append($row);
        if (v.canEditStops && window.Pickr) {
            initPickr(`#stop_picker_${index}`, `#stop_input_${index}`, (text) => {
                const rgb = parseRgbText(text);
                if (rgb) {
                    draft.stops = setStop(draft.stops, index, rgb);
                    renderActions();
                }
            }, rgbCss(stop));
        }
    });
};

/** Replace the stops and rebuild the stop list, as the pickers hold their own colour. */
const edit = (stops) => {
    if (stops === draft.stops) return;
    draft.stops = stops;
    render();
};

const render = () => {
    $('#kind_tabs .nav-link').each(function () { $(this).toggleClass('active', $(this).attr('data-kind') === kind); });
    $('#new_btn').text(`+ New ${KINDS[kind].singular}`);
    renderList();
    $('#editor').toggleClass('d-none', draft === null);
    $('#editor_empty').toggleClass('d-none', draft !== null);
    $('#message').addClass('d-none');
    if (draft === null) return;

    const v = view();
    $('#notice').toggleClass('d-none', !v.notice).text(v.notice ?? '');
    $('#predefined_badge').toggleClass('d-none', !v.badge);
    $('#entry_name').val(draft.name).prop('disabled', !v.canEditName);
    $('#stops_label').text(kind === COLOUR ? 'Colour' : 'Colour stops (evenly spaced)');
    renderStops(v);
    renderActions();
};

const renderList = () => {
    const $list = $('#entry_list').empty();
    entries[kind].forEach((item) => {
        const $name = $('<div></div>').text(item.name);
        if (item.predefined) $name.append(' ', '<span class="badge badge-secondary">Predefined</span>');
        const css = previewCss(entryStops(item));
        const $body = $('<div class="flex-grow-1"></div>').append($name);
        if (kind === GRADIENT) $body.append($('<div class="entry-bar mt-1"></div>').css('background', css));
        const $item = $('<div class="entry-item d-flex align-items-center"></div>').attr('data-name', item.name).on('click', () => open(item));
        if (kind === COLOUR) $item.append($('<span class="entry-swatch mr-2"></span>').css('background', css));
        $list.append($item.append($body));
    });
};

const load = async (select) => {
    const [gradients, colours] = await Promise.all([api.get('/gradients'), api.get('/colors')]);
    entries[GRADIENT] = gradients;
    entries[COLOUR] = colours;
    const wanted = select ? entries[kind].find(item => item.name.toLowerCase() === select.toLowerCase()) : null;
    if (wanted) open(wanted);
    else {
        entry = null;
        draft = null;
        render();
    }
};

/** Run a request with every button off, and report a failure as a toast or in the panel. */
const run = async (action, failure) => {
    busy = true;
    renderActions();
    try {
        await action();
    } catch (error) {
        if (error.code === 'EntryInUse' && error.usages) {
            showMessage('danger', deleteBlockedMessage(entry.name, error.usages, targetNames));
        } else {
            new Toast(`${failure} ${error.summary ?? error.message}`).error();
        }
    } finally {
        busy = false;
        if (draft) renderActions();
    }
};

const save = () => run(async () => {
    const v = view();
    const name = draft.name.trim();
    const saved = entry
        ? await api.patch(entryPath(kind, entry.name), payloadOf(kind, name, draft.stops))
        : await api.post(KINDS[kind].path, payloadOf(kind, name, draft.stops));
    await load(saved.name);
    new Toast(`Saved "${saved.name}".${v.saveWarning ? ' The devices that use it were restarted.' : ''}`).success();
}, 'Could not save.');

const duplicate = () => run(async () => {
    const copy = await api.post(`${entryPath(kind, entry.name)}/duplicate`);
    await load(copy.name);
    new Toast(`Duplicated as "${copy.name}".`).success();
}, 'Could not duplicate.');

const remove = () => {
    if (!window.confirm(`Delete "${entry.name}"?`)) return Promise.resolve();
    return run(async () => {
        const name = entry.name;
        await api.delete(entryPath(kind, name));
        await load();
        new Toast(`Deleted "${name}".`).success();
    }, 'Could not delete.');
};

$(() => {
    $('.navbar-content').trigger('mouseover');

    load().catch(error => new Toast(`Error while loading gradients and colours. ${error.summary ?? error.message}`).error());

    $('#kind_tabs .nav-link').on('click', (event) => {
        kind = $(event.currentTarget).attr('data-kind');
        entry = null;
        draft = null;
        render();
    });
    $('#new_btn').on('click', () => open(null));
    $('#entry_name').on('input', (event) => {
        draft.name = event.currentTarget.value;
        renderActions();
    });
    $('#add_stop_btn').on('click', () => edit(addStop(draft.stops)));
    $('#save_btn').on('click', save);
    $('#duplicate_btn').on('click', duplicate);
    $('#delete_btn').on('click', remove);
});
