from libs.webserver.executer_base import ExecuterBase

from configparser import ConfigParser, ParsingError, MissingSectionHeaderError
from flask import render_template, request, jsonify, send_file, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from urllib.parse import urlparse, urljoin
from os import chmod
import re

login_manager = LoginManager()

class AuthenticationExecuter(ExecuterBase):
          
    def add_server_authentication(self, server):

        self.default_values = {
        "DEFAULT_PIN": "",
        "USE_PIN_LOCK": False
        }       

        self.pin_config = ConfigParser()
        self.pin_file = '../security.ini'
        self.file_values = self.read_pin_file()
        self.DEFAULT_PIN = self.file_values["DEFAULT_PIN"]
        self.USE_PIN_LOCK = self.file_values["USE_PIN_LOCK"]
        
        if not self.validate_pin(self.DEFAULT_PIN) and self.USE_PIN_LOCK:
            raise ValueError("PIN must be from 4 to 8 digits.")
        
        server.secret_key = 'secretkey'
        if not self.USE_PIN_LOCK:
            server.config['LOGIN_DISABLED'] = True
        login_manager.init_app(server)

        return server
    
    def save_pin_file(self):
        with open(self.pin_file, 'w') as configfile:
            self.pin_config.write(configfile)
            chmod(self.pin_file, 775)


    def reset_pin_file(self):
        for section in self.pin_config.sections():
            self.pin_config.remove_section(section)
        self.pin_config["SECURITY"] = self.default_values
        self.save_pin_file()


    def read_pin_file(self):
        # Check if .ini file exists and if security options are valid.
        self.file_values = self.default_values
        try:
            dataset = self.pin_config.read(self.pin_file)
        except (ParsingError, MissingSectionHeaderError):
            self.reset_pin_file()
            dataset = self.pin_config.read(self.pin_file)

        if self.pin_file in dataset:
            try:
                self.file_values["DEFAULT_PIN"] = self.pin_config['SECURITY'].get('DEFAULT_PIN')
                self.file_values["USE_PIN_LOCK"] = self.pin_config['SECURITY'].getboolean('USE_PIN_LOCK')
                return self.file_values
            except (ValueError, KeyError):
                self.reset_pin_file()
                return self.file_values
        else:
            self.reset_pin_file()
        return self.file_values


    def validate_pin(self, pin):
        return bool(re.fullmatch(r"\d{4,8}", pin))
  
    def is_safe_url(self, target):
        ref_url = urlparse(request.host_url)
        test_url = urlparse(urljoin(request.host_url, target))
        return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

    def first_call(self):
        if self.USE_PIN_LOCK:
            logout_user()

    def set_pin_setting(self, data):
        self.pin_config["SECURITY"] = data
        self.save_pin_file()
      
    def get_pin_setting(self):
        return self.read_pin_file()

    def reset_pin_settings(self, data):
        self.pin_config["SECURITY"] = data
        self.save_pin_file()
        return self.read_pin_file()

    def login(self):
        user = User()
        login_user(user)

    @login_manager.user_loader
    def user_loader(user_id):
        if not Executer.authentication_executer.USE_PIN_LOCK:
            return
        user = User()
        user.id = user_id
        return user

    @login_manager.unauthorized_handler
    def unauthorized():
        session['next'] = request.path
        return redirect(url_for('login', next=session['next']))

class User(UserMixin):
        id = 1001