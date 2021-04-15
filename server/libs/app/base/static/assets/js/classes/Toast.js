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

export default class Toast {
    constructor(message) {
        this.message = message;
    }

    _base(type) {
        const style = types[type];
        const toast = `
            <div class="toast toast_bg" style="min-width: 250px;" role="alert" aria-live="assertive" aria-atomic="true" data-delay="5000">
                <div class="toast-header">
                    <strong class="mr-auto ${style.class} "><i class="feather ${style.icon}"></i> ${style.title}</strong>
                    <small class="text-muted">${new Date().toLocaleTimeString()}</small>
                    <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="Close">
                        <span aria-hidden="true" class="feather icon-x"></span>
                    </button>
                </div>
                <div class="toast-body">
                    ${this.message}
                </div>
            </div>
        `;

        $(".toast_block").prepend(toast);
        $('.toast').toast('show').on('hidden.bs.toast', function () {
            $(this).remove();
        })

        return toast;
    }

    success() {
        return this._base("success");
    }

    warning() {
        return this._base("warning");
    }

    error() {
        return this._base("error");
    }

    info() {
        return this._base("info");
    }
}
