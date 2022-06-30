const types = {
    "success": {
        "class": "text-success",
        "icon": "icon-check",
        "title": "Success"
    },
    "warning": {
        "class": "text-warning",
        "icon": "icon-alert-circle",
        "title": "Warning"
    },
    "error": {
        "class": "text-danger",
        "icon": "icon-alert-triangle",
        "title": "Error"
    },
    "info": {
        "class": "text-info",
        "icon": "icon-info",
        "title": "Information"
    },
};

// Detect when toast animation ends
const animationEnd = (function (el) {
    const animations = {
        "animation": "animationend",
        "OAnimation": "oAnimationEnd",
        "MozAnimation": "mozAnimationEnd",
        "WebkitAnimation": "webkitAnimationEnd"
    };
    for (var t in animations) {
        if (el.style[t] !== undefined) {
            return animations[t];
        }
    }
})(document.createElement("div"));

export default class Toast {
    /**
     * Create toast with custom message.
     * @param {string} message
     */
    constructor(message) {
        /** @private */
        this.message = message;
    }

    /**
     * Build toast from base.
     * @param {string} type
     * @private
     * @return {string}
     */
    _base(type) {
        const style = types[type];
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
                    ${this.message}
                </div>
            </div>
        `;

        $(".toast_block").prepend(toast);
        const curToast = $('.toast').toast('show')

        // Hide toast after 5 seconds
        setTimeout(function () {
            $(curToast).addClass("animated fadeOutRight");
            $(curToast).one(animationEnd, function () {
                $(this).remove();
            });
        }, 5000);

        // Hide toast after clicking X button
        $(".close").on('click', function () {
            $(this).parents().eq(1).addClass("animated fadeOutRight");
            $(this).parents().eq(1).one(animationEnd, function () {
                $(this).remove();
            });
        })

        return toast;
    }

    /**
     * Build Success toast.
     * @return {string}
     */
    success() {
        return this._base("success");
    }

    /**
     * Build Warning toast.
     * @return {string}
     */
    warning() {
        return this._base("warning");
    }

    /**
     * Build Error toast.
     * @return {string}
     */
    error() {
        return this._base("error");
    }

    /**
     * Build Information toast.
     * @return {string}
     */
    info() {
        return this._base("info");
    }
}
