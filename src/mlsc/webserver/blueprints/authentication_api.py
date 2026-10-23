from flask import flash, jsonify, redirect, render_template, request, session, url_for
from flask_openapi3 import APIBlueprint

from mlsc.webserver import auth
from mlsc.webserver.executer import Executer
from mlsc.webserver.openapi_docs import doc

authentication_api = APIBlueprint("authentication_api", __name__)


@authentication_api.get("/login")
def show_login_page():
    is_pin_active = Executer.instance.authentication_executer.is_pin_active()
    is_authenticated = auth.is_authenticated()

    if not is_pin_active or is_authenticated:
        return redirect(url_for("home_blueprint.index"))

    return render_template("home/login.html")


@authentication_api.post("/login", **doc("authentication_api/login.yml"))
def login():
    """Log in user."""
    pin = request.form.get("pin")

    if not pin:
        flash("PIN is required")
    elif not pin.isdigit():
        flash("PIN must only contain digits")
    elif not Executer.instance.authentication_executer.validate_pin(pin):
        flash("PIN must be at least 4 digits long")
    elif pin != Executer.instance.authentication_executer.USER_PIN:
        flash("Invalid PIN")

    elif pin == Executer.instance.authentication_executer.USER_PIN:
        Executer.instance.authentication_executer.login()
        if session.get("next") is not None:
            next_page = session["next"]
            session["next"] = None
            if Executer.instance.authentication_executer.is_safe_url(next_page):
                return redirect(next_page)
        return redirect(url_for("home_blueprint.index"))

    return redirect(url_for("authentication_api.login", next=session.get("next")))


@authentication_api.get("/logout", **doc("authentication_api/logout.yml"))
def logout():
    """Log out user."""
    auth.logout_user()
    return redirect(url_for("authentication_api.login"))


@authentication_api.get("/api/auth/pin", **doc("authentication_api/get_pin_setting.yml"))
def get_pin_setting():
    """Return PIN code."""
    is_pin_active = Executer.instance.authentication_executer.is_pin_active()
    is_authenticated = auth.is_authenticated()

    if not is_pin_active or is_authenticated:
        data_in = Executer.instance.authentication_executer.get_pin_setting()
        data_out = {
            "DEFAULT_PIN": data_in["DEFAULT_PIN"],
            "USE_PIN_LOCK": data_in["USE_PIN_LOCK"]
        }
        return jsonify(data_out)

    return "Unauthorized", 401


@authentication_api.post("/api/auth/pin", **doc("authentication_api/set_pin_setting.yml"))
def set_pin_setting():
    """Set PIN code."""
    is_pin_active = Executer.instance.authentication_executer.is_pin_active()
    is_authenticated = auth.is_authenticated()

    if not is_pin_active or is_authenticated:
        data_in = request.get_json()

        data_out = {
            "DEFAULT_PIN": data_in["DEFAULT_PIN"],
            "USE_PIN_LOCK": data_in["USE_PIN_LOCK"]
        }
        Executer.instance.authentication_executer.set_pin_setting(data_out)
        return jsonify(data_out)

    return "Unauthorized", 401


@authentication_api.delete("/api/auth/pin", **doc("authentication_api/reset_pin_setting.yml"))
def reset_pin_setting():
    """Reset PIN code."""
    is_pin_active = Executer.instance.authentication_executer.is_pin_active()
    is_authenticated = auth.is_authenticated()

    if not is_pin_active or is_authenticated:
        data_out = Executer.instance.authentication_executer.reset_pin_settings()
        return jsonify(data_out)

    return "Unauthorized", 401
