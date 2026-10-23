const types = {
    success: {
        class: 'text-success',
        icon: 'icon-check',
        title: 'Success'
    },
    warning: {
        class: 'text-warning',
        icon: 'icon-alert-circle',
        title: 'Warning'
    },
    error: {
        class: 'text-danger',
        icon: 'icon-alert-triangle',
        title: 'Error'
    },
    info: {
        class: 'text-info',
        icon: 'icon-info',
        title: 'Information'
    }
};


export default class Toast {
    /**
     * Create toast with custom message.
     * Set `showButton` to `true` to show a button that links to the device settings page.
     * @param {string} message
     * @param {boolean} showButton - Default: `false`
     */
    constructor(message, showButton = false) {
        /** @private */
        this.message = message;
        /** @private */
        this.showButton = showButton;
    }

    /**
     * Build toast from base.
     * @param {string} type
     * @private
     * @return {string}
     */
    _base(type) {
        const style = types[type];

        let settingsBtn = '';
        if (this.showButton) {
            settingsBtn = `
                <div class="toast_button">
                    <button type="button" onclick="location.href='/settings/device_settings';" class="btn btn-secondary btn-sm m-0">Go to settings</button>
                </div>
            `;
        }

        const toast = `
            <div class="toast toast_bg animated fadeInRight" style="min-width: 250px;" role="alert" aria-live="assertive" aria-atomic="true" data-autohide="false">
                <div class="toast-header">
                    <strong class="mr-auto ${style.class}"><i class="feather ${style.icon}"></i> ${style.title}</strong>
                    <small class="text-muted">${new Date().toLocaleTimeString()}</small>
                    <button type="button" class="ml-2 mb-1 close" aria-label="Close">
                        <span aria-hidden="true" class="feather icon-x"></span>
                    </button>
                </div>
                <div class="toast-body">
                    <span class="d-block">
                        ${this.message}
                    </span>
                    ${settingsBtn}
                </div>
            </div>
        `;

        $('.toast_block').prepend(toast);
        const curToast = $('.toast').toast('show');

        // Hide toast after 6 seconds.
        setTimeout(() => {
            $(curToast).addClass('fadeOutRight').one('animationend', e => {
                $(e.target).remove();
            });
        }, 6000);

        // Hide toast after clicking X button.
        $('.close').on('click', e => {
            $(e.currentTarget).parents().eq(1).addClass('fadeOutRight').one('animationend', e => {
                $(e.target).remove();
            });
        })

        return toast;
    }

    /**
     * Build Success toast.
     * @return {string}
     */
    success() {
        return this._base('success');
    }

    /**
     * Build Warning toast.
     * @return {string}
     */
    warning() {
        return this._base('warning');
    }

    /**
     * Build Error toast.
     * @return {string}
     */
    error() {
        return this._base('error');
    }

    /**
     * Build Information toast.
     * @return {string}
     */
    info() {
        return this._base('info');
    }
}
