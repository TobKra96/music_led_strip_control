export default class Tagin {
    /**
    * Create a new Tagin instance.
    *
    * @param el - Element anchor.
    * @param option - Customization options.
    *
    * @example
    * ```js
    * var options = {
    *     separator: ',', // default: ','
    *     duplicate: false, // default: false
    *     enter: true, // default: false
    *     transform: input => input.toUpperCase(), // default: input => input
    *     placeholder: 'Enter tags...' // default: ''
    * };
    * var tagin = new Tagin(document.getElementById('tagin'), options);
    * ```
    */
    constructor(el, option = {}) {
        const classElement = 'tagin';
        const classWrapper = 'tagin-wrapper';
        const classTag = 'tagin-tag';
        const classRemove = 'tagin-tag-remove';
        const classInput = 'tagin-input';
        const classInputHidden = 'tagin-input-hidden';
        const defaultSeparator = ',';
        const defaultDuplicate = 'false';
        const defaultEnter = 'false';
        const defaultTransform = input => input;
        const defaultPlaceholder = '';
        const separator = el.dataset.separator || option.separator || defaultSeparator;
        const duplicate = el.dataset.duplicate || option.duplicate || defaultDuplicate;
        const enter = el.dataset.enter || option.enter || defaultEnter;
        const transform = eval(el.dataset.transform) || option.transform || defaultTransform;
        const placeholder = el.dataset.placeholder || option.placeholder || defaultPlaceholder;

        const templateTag = value => `<span class="${classTag}">${value}<span class="${classRemove}"></span></span>`;

        const getValue = () => el.value;
        const getValues = () => getValue().split(separator); (function () {
            const className = classWrapper + ' ' + el.className.replace(classElement, '').replace("setting_input", '').trim();
            const tags = getValue().trim() === '' ? '' : getValues().map(templateTag).join('');
            const template = `<div class="${className}">${tags}<input type="text" class="${classInput}" placeholder="${placeholder}"></div>`;
            el.insertAdjacentHTML('afterend', template); // insert template after element
        })();

        const wrapper = el.nextElementSibling;
        const input = wrapper.getElementsByClassName(classInput)[0];
        const getTags = () => [...wrapper.getElementsByClassName(classTag)].map(tag => tag.textContent);
        const getTag = () => getTags().join(separator);

        const updateValue = () => { el.value = getTag(); el.dispatchEvent(new Event('change')) };

        // Focus to input
        wrapper.addEventListener('click', () => input.focus());

        // Toggle focus class
        input.addEventListener('focus', () => wrapper.classList.add('focus'));
        input.addEventListener('blur', () => wrapper.classList.remove('focus'));

        // Remove by click
        document.addEventListener('click', e => {
            if (e.target.closest('.' + classRemove)) {
                e.target.closest('.' + classRemove).parentNode.remove();
                updateValue();
            }
        });

        // Remove with backspace
        input.addEventListener('keydown', e => {
            if (input.value === '' && e.keyCode === 8 && wrapper.getElementsByClassName(classTag).length) {
                wrapper.querySelector('.' + classTag + ':last-of-type').remove();
                updateValue();
            }
            if (input.value !== '' && e.keyCode === 13 && (enter === "true" || enter === true)) {
                this.addTag(true, transform(input.value.trim()));
                e.preventDefault();
            }
        });

        // Adding tag
        input.addEventListener('input', () => {
            this.addTag(false, transform(input.value.trim()));
        })
        input.addEventListener('blur', () => {
            this.addTag(true, transform(input.value.trim()));
        })

        function autowidth() {
            const fakeEl = document.createElement('div');
            fakeEl.classList.add(classInput, classInputHidden);
            const string = input.value || input.getAttribute('placeholder') || '';
            fakeEl.innerHTML = string.replace(/ /g, '&nbsp;');
            document.body.appendChild(fakeEl);
            input.style.setProperty('width', Math.ceil(window.getComputedStyle(fakeEl).width.replace('px', '')) + 1 + 'px');
            fakeEl.remove();
        }

        /**
        * Adds a tag or multiple tags.
        *
        * @param force - Add tag even without separator (bool)
        * @param tagName - The tag name(s) to add (string)
        *
        * @example
        * Multiple tags should be a comma separated string:
        * ```js
        * this.addTag(true, 'NewTag')
        * this.addTag(false, 'OneTag, TwoTag, ThreeTag')
        * let tagArray = ['OneTag', 'TwoTag', 'ThreeTag']
        * this.addTag(false, tagArray.join(', '))
        * ```
        */
        this.addTag = (force = false, tagName = '') => {
            if (tagName === '') { input.value = ''; }
            if (tagName.includes(separator) || (force && tagName != '')) {
                tagName.split(separator).filter(i => i != '').forEach(val => {
                    if (getTags().includes(val) && (duplicate === 'false' || duplicate === false)) {
                        alertExist(val);
                    } else {
                        input.insertAdjacentHTML('beforebegin', templateTag(val));
                        updateValue();
                    }
                })
                input.value = '';
                input.removeAttribute('style');
            }
            autowidth();
        }

        /**
        * Returns an array of tags.
        *
        * @returns array
        */
        this.getTags = () => {
            return getTags().map(s => s.trim());;
        };

        function alertExist(value) {
            for (const el of wrapper.getElementsByClassName(classTag)) {
                if (el.textContent === value) {
                    el.style.transform = 'scale(1.09)';
                    setTimeout(() => { el.removeAttribute('style') }, 150);
                }
            }
        }

        function updateTag() {
            if (getValue() !== getTag()) {
                [...wrapper.getElementsByClassName(classTag)].map(tag => tag.remove());
                getValue().trim() !== '' && input.insertAdjacentHTML('beforebegin', getValues().map(templateTag).join(''));
            }
        }

        autowidth();
        el.addEventListener('change', () => updateTag());
    }
}

if (typeof exports === 'object' && typeof module !== 'undefined') {
    module.exports = Tagin;
}
