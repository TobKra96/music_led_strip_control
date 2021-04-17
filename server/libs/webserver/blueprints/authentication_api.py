from flask import Blueprint, request, jsonify
from flask_login import login_required
from libs.webserver.executer import Executer
from flask import render_template, request, jsonify, send_file, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required

import copy
import json

authentication_api = Blueprint('authentication_api', __name__)

#@authentication_api.before_first_request

@authentication_api.before_app_first_request
def first():
    Executer.instance.authentication_executer.first_call()


@authentication_api.route('/login', methods=['GET', 'POST'])
def login():
    use_pin_lock = Executer.instance.authentication_executer.get_use_pin_lock()
    is_authenticated = current_user.is_authenticated

    if not use_pin_lock or is_authenticated:
        return redirect("/")
    if request.method == 'POST':
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
        elif pin == Executer.instance.authentication_executer.DEFAULT_PIN:
            Executer.instance.authentication_executer.login()
            if session['next'] is not None:
                if Executer.instance.authentication_executer.is_safe_url(session['next']):
                    return redirect(session['next'])
            return redirect("/")
    return render_template('login.html')


@authentication_api.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('login'))



@authentication_api.route('/SetPinSetting', methods=['POST'])
@login_required
def SetPinSetting():  # pylint: disable=E0211
    data_in = request.get_json()

    data_out = {
        "DEFAULT_PIN": data_in["DEFAULT_PIN"],
        "USE_PIN_LOCK": data_in["USE_PIN_LOCK"]
    }
    Executer.instance.authentication_executer.set_pin_setting(data_out)
    return jsonify(data_out)

@authentication_api.route('/GetPinSetting', methods=['GET'])
@login_required
def GetPinSetting():  # pylint: disable=E0211
    data_in = Executer.instance.authentication_executer.get_pin_setting()
    data_out = {
        "DEFAULT_PIN": data_in["DEFAULT_PIN"],
        "USE_PIN_LOCK": data_in["USE_PIN_LOCK"]
    }
    return jsonify(data_out)

@authentication_api.route('/ResetPinSettings', methods=['POST'])
@login_required
def ResetPinSettings():  # pylint: disable=E0211
    data_in = request.get_json()
    new_values = {
        "DEFAULT_PIN": data_in["DEFAULT_PIN"],
        "USE_PIN_LOCK": data_in["USE_PIN_LOCK"]
    }
    
    data_out = Executer.instance.authentication_executer.reset_pin_settings(new_values)
    return jsonify(data_out)