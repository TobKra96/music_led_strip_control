const levels = {
    info: { class: 'alert-info', icon: 'icon-info' },
    success: { class: 'alert-success', icon: 'icon-check' },
    warning: { class: 'alert-warning', icon: 'icon-alert-circle' },
    error: { class: 'alert-danger', icon: 'icon-alert-triangle' },
};

/**
 * A persistent message at the top of the page. Unlike a toast it stays until the problem is gone or the user dismisses it.
 * A banner is identified by its `id`: showing the same id again replaces the old one.
 */
export default class Banner {
    /**
     * @param {string} id Identifies the banner, e.g. `connection`, `diagnosis-device_0`, `migration-report`.
     */
    constructor(id) {
        this.id = id;
    }

    /**
     * Show the banner. All text is inserted as text, never as HTML.
     * @param {{level?: string, title?: string, message: string, details?: Array.<string>, onDismiss?: function(): void,
     *   actions?: Array.<{label: string, onClick: function(): void}>}} options
     *   `details` are listed in a collapsible section. A banner with `onDismiss` gets a close button, one with `actions` a button for each.
     * @return {Banner}
     */
    show({ level = 'info', title = '', message, details = [], onDismiss, actions = [] }) {
        const style = levels[level] || levels.info;
        const $banner = $('<div class="alert mlsc-banner mb-3" role="alert"></div>')
            .addClass(style.class)
            .attr('data-banner-id', this.id);

        const $heading = $('<div class="d-flex align-items-start"></div>');
        $heading.append($('<i class="feather mr-2 mt-1" aria-hidden="true"></i>').addClass(style.icon));
        const $text = $('<div class="flex-grow-1"></div>');
        if (title) $text.append($('<strong class="d-block"></strong>').text(title));
        $text.append($('<span></span>').text(message));
        $heading.append($text);

        if (onDismiss) {
            const $close = $('<button type="button" class="close ml-2" aria-label="Dismiss"><span aria-hidden="true">&times;</span></button>');
            $close.on('click', () => {
                this.hide();
                onDismiss();
            });
            $heading.append($close);
        }
        $banner.append($heading);

        if (actions.length) {
            const $actions = $('<div class="mt-2"></div>');
            actions.forEach(({ label, onClick }) => {
                $actions.append($('<button type="button" class="btn btn-sm btn-outline-secondary mr-2"></button>').text(label).on('click', onClick));
            });
            $banner.append($actions);
        }

        if (details.length) {
            const $list = $('<ul class="mb-0 mt-2 pl-4 d-none"></ul>');
            details.forEach(detail => $list.append($('<li></li>').text(detail)));
            const $toggle = $('<a href="#!" class="d-inline-block mt-2">Show details</a>');
            $toggle.on('click', e => {
                e.preventDefault();
                const hidden = $list.toggleClass('d-none').hasClass('d-none');
                $toggle.text(hidden ? 'Show details' : 'Hide details');
            });
            $banner.append($toggle, $list);
        }

        this.hide();
        $('#banner_block').append($banner);
        return this;
    }

    /** Remove the banner if it is shown. */
    hide() {
        $('#banner_block').children().filter((_, el) => el.getAttribute('data-banner-id') === this.id).remove();
    }
}
