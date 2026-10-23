/**
 * @typedef {import("../../plugins/pickr/js/pickr")} Pickr
 * @typedef {Pickr.HSVaColor} HSVaColor
 * @typedef {Pickr.Source} Source
*/

/**
 * Initialize Pickr if required elements are present.
 * @param {string} parent - Color picker element id.
 * @param {string} input - Input field element class or id.
 */
const initPickr = (parent, input) => {
    const parentEl = document.querySelector(parent);
    const inputEl = document.querySelector(input);

    if (!parentEl || !inputEl) {
        return;
    }

    Pickr.create({
        el: parentEl,
        input: inputEl,  // Custom option to pass input field to Pickr.
        theme: 'monolith',
        default: 'rgb(255,255,255)',
        position: 'left-middle',
        lockOpacity: false,
        comparison: false,
        useAsButton: true,

        swatches: [
            'rgb(244, 67, 54)',
            'rgb(233, 30, 99)',
            'rgb(156, 39, 176)',
            'rgb(103, 58, 183)',
            'rgb(63, 81, 181)',
            'rgb(33, 150, 243)',
            'rgb(3, 169, 244)',
            'rgb(0, 188, 212)',
            'rgb(0, 150, 136)',
            'rgb(76, 175, 80)',
            'rgb(139, 195, 74)',
            'rgb(205, 220, 57)',
            'rgb(255, 235, 59)',
            'rgb(255, 193, 7)'
        ],

        components: {
            hue: true
        }
    }).on('init', (/** @type {Pickr} */ pickr) => {

        // Parse and validate RGB on change or input.
        $(pickr.options.input).on('input change', (/** @type {JQuery.Event} */ e) => {
            const formattedRGB = formatRGB(validateRGB(parseRGB(e.currentTarget.value)));
            pickr.setColor(formattedRGB);
        });

        _updateStyles(pickr);

    }).on('change', (/** @type {HSVaColor} */ c, /** @type {Source} */ s, /** @type {Pickr} */ pickr) => {
        _updateStyles(pickr);
    });
}

/**
 * Update Color Picker and Input field.
 * @param {Pickr} pickr
 */
const _updateStyles = (pickr) => {
    const newColor = pickr.getColor().toRGBA().toString(0).replace(', 1)', ')').replace('rgba', 'rgb');
    pickr.options.el.style.background = newColor;
    pickr.options.input.value = newColor;
}

/**
 * Parse "rgb(r,g,b)" into [r,g,b].
 * @param {string} rgb
 * @return {Array.<number>}
 */
const parseRGB = (rgb) => rgb.replace(/[^\d,]/g, '').split(",").map(Number);

/**
 * Validate if [r,g,b] is a valid RGB value.
 * @param {Array.<number>} rgb
 * @return {Array.<number>}
 */
const validateRGB = (rgb) => {
    return rgb.length === 3 ? rgb.map(val => {
        if (isNaN(val) || val < 0) {
            return 0;
        }
        if (val > 255) {
            return 255;
        }
        return val;
    }) : [0, 0, 0];
}

/**
 * Format [r,g,b] into "rgb(r,g,b)".
 * @param {Array.<number>} rgb
 * @return {string}
 */
const formatRGB = (rgb) => `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;

export { initPickr, formatRGB, parseRGB, validateRGB };
