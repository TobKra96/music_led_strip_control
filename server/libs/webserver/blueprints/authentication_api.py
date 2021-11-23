from libs.webserver.executer import Executer

from flask import render_template, request, jsonify, redirect, url_for, session, flash, Blueprint
from flask_login import current_user, logout_user, login_required

authentication_api = Blueprint('authentication_api', __name__)


@authentication_api.before_app_first_request
def first():
    Executer.instance.authentication_executer.first_call()


@authentication_api.get('/login')
def show_login_page():
    use_pin_lock = Executer.instance.authentication_executer.get_use_pin_lock()
    is_authenticated = current_user.is_authenticated

    if not use_pin_lock or is_authenticated:
        return redirect("/")

    return render_template('login.html')


@authentication_api.post('/login')
def login():
    """
    Log in user
    ---
    tags:
      - Auth
    requestBody:
      content:
        application/x-www-form-urlencoded:
          schema:
            type: object
            properties:
              pin:
                description: Redirects to next page if login successful
                type: string
            required:
              - pin
      responses:
        "200":
          description: OK
    """
    pin = request.form.get('pin')
    if 'next' in request.args:
        session['next'] = request.args['next']
    else:
        session['next'] = None
    if not pin:
        flash('PIN is required')
        return redirect(url_for('authentication_api.login', next=session['next']))
    if not pin.isdigit():
        flash('PIN must only contain digits')
        return redirect(url_for('authentication_api.login', next=session['next']))
    if not Executer.instance.authentication_executer.validate_pin(pin):
        flash('PIN must be at least 4 digits long')
        return redirect(url_for('authentication_api.login', next=session['next']))
    if pin != Executer.instance.authentication_executer.DEFAULT_PIN:
        flash('Invalid PIN')
        return redirect(url_for('authentication_api.login', next=session['next']))
    if pin == Executer.instance.authentication_executer.DEFAULT_PIN:
        Executer.instance.authentication_executer.login()
        if session['next'] is not None:
            if Executer.instance.authentication_executer.is_safe_url(session['next']):
                return redirect(session['next'])
        return redirect("/")
    return render_template('login.html')


@authentication_api.get('/logout')
def logout():
    """
    Log out user
    ---
    tags:
      - Auth
    description:
      Redirects to login page if PIN code is enabled\n\n
      Else, redirects to dashboard
    responses:
      "200":
        description: OK
        content:
          text/html:
            schema:
              type: string
    """
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('authentication_api.login'))


@authentication_api.get('/api/auth/pin')
def get_pin_setting():  # pylint: disable=E0211
    """
    Return PIN code
    ---
    tags:
      - Auth
    description: Returning PIN is allowed only when logged in or when PIN lock is disabled
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                DEFAULT_PIN: str
                USE_PIN_LOCK: bool
              type: object
      "401":
        description: Unauthorized
    """
    use_pin_lock = Executer.instance.authentication_executer.get_use_pin_lock()
    is_authenticated = current_user.is_authenticated

    if not use_pin_lock or is_authenticated:
        data_in = Executer.instance.authentication_executer.get_pin_setting()
        data_out = {
            "DEFAULT_PIN": data_in["DEFAULT_PIN"],
            "USE_PIN_LOCK": data_in["USE_PIN_LOCK"]
        }
        return jsonify(data_out)

    return "Unauthorized", 401


@authentication_api.post('/api/auth/pin')
def set_pin_setting():  # pylint: disable=E0211
    """
    Set PIN code
    ---
    tags:
      - Auth
    description: Setting PIN is allowed only when logged in or when PIN lock is disabled
    requestBody:
      content:
        application/json:
          schema:
            type: string
          examples:
            example1:
              value:
                DEFAULT_PIN: 1111
                USE_PIN_LOCK: true
              summary: 4 digit active PIN
      description: 4-8 digit PIN code and active lock state
      required: true
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                DEFAULT_PIN: str
                USE_PIN_LOCK: bool
              type: object
      "401":
        description: Unauthorized
    """
    use_pin_lock = Executer.instance.authentication_executer.get_use_pin_lock()
    is_authenticated = current_user.is_authenticated

    if not use_pin_lock or is_authenticated:
        data_in = request.get_json()

        data_out = {
            "DEFAULT_PIN": data_in["DEFAULT_PIN"],
            "USE_PIN_LOCK": data_in["USE_PIN_LOCK"]
        }
        Executer.instance.authentication_executer.set_pin_setting(data_out)
        return jsonify(data_out)

    return "Unauthorized", 401


@authentication_api.delete('/api/auth/pin')
def reset_pin_setting():  # pylint: disable=E0211
    """
    Reset PIN code
    ---
    tags:
      - Auth
    description: Resetting PIN is allowed only when logged in or when PIN lock is disabled
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                DEFAULT_PIN: str
                USE_PIN_LOCK: bool
              type: object
      "401":
        description: Unauthorized
    """
    use_pin_lock = Executer.instance.authentication_executer.get_use_pin_lock()
    is_authenticated = current_user.is_authenticated

    if not use_pin_lock or is_authenticated:
        data_out = Executer.instance.authentication_executer.reset_pin_settings()
        return jsonify(data_out)

    return "Unauthorized", 401
