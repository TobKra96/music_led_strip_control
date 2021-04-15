export default class Toast {
    constructor(message) {
        this.message = message;
        this.types = {
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
    }

    base(type) {
        let style = this.types[type];
        let toast = `
            <div class="toast toast_bg" style="min-width: 250px;" role="alert" aria-live="assertive" aria-atomic="true" data-delay="5000">
                <div class="toast-header">
                    <strong class="mr-auto ` + style.class + `"><i class="feather ` + style.icon + `"></i> ` + style.title + `</strong>
                    <small class="text-muted">` + new Date().toLocaleTimeString('en-GB') + `</small>
                    <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="Close">
                        <span aria-hidden="true" class="feather icon-x"></span>
                    </button>
                </div>
                <div class="toast-body">
                    ` + this.message + `
                </div>
            </div>
        `;
        return toast;
    }

    success() {
        return this.base("success");
    }

    warning() {
        return this.base("warning");
    }

    error() {
        return this.base("error");
    }

    info() {
        return this.base("info");
    }
}
