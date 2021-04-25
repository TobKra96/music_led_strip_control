from libs.webserver.executer_base import ExecuterBase

from configparser import ConfigParser, ParsingError, MissingSectionHeaderError
from flask_login import LoginManager, UserMixin, login_user, logout_user
from flask import request, redirect, url_for, session
from urllib.parse import urlparse, urljoin
from os import chmod
import re

USE_PIN_LOCK = True
login_manager = LoginManager()


@login_manager.user_loader
def user_loader(user_id):
    print("user loader")
    if not USE_PIN_LOCK:
        return
    user = User()
    user.id = user_id
    return user


@login_manager.unauthorized_handler
def unauthorized():
    print("unauthorized")
    session['next'] = request.path
    return redirect(url_for('authentication_api.login', next=session['next']))


class AuthenticationExecuter(ExecuterBase):

    def add_server_authentication(self, server):
        self.logger.debug("Enter add_server_authentication()")
        self.default_values = {
            "DEFAULT_PIN": "",
            "USE_PIN_LOCK": False
        }

        self.pin_config = ConfigParser()
        self.pin_file = '../security.ini'
        self.file_values = self.read_pin_file()
        self.DEFAULT_PIN = self.file_values["DEFAULT_PIN"]
        USE_PIN_LOCK = self.file_values["USE_PIN_LOCK"]

        self.logger.debug(f"USE_PIN_LOCK: {USE_PIN_LOCK}")

        if not self.validate_pin(self.DEFAULT_PIN) and USE_PIN_LOCK:
            raise ValueError("PIN must be from 4 to 8 digits.")

        server.secret_key = 'secretkey'
        if not USE_PIN_LOCK:
            server.config['LOGIN_DISABLED'] = True
        login_manager.init_app(server)

        return server

    def save_pin_file(self):
        self.logger.debug("Save Pin to file.")
        with open(self.pin_file, 'w') as configfile:
            self.logger.debug("Write pin to file.")
            self.pin_config.write(configfile)
            chmod(self.pin_file, 775)
        self.logger.debug("Pin saved to file.")

    def reset_pin_file(self):
        self.logger.debug("Reset pin")
        for section in self.pin_config.sections():
            self.pin_config.remove_section(section)
        self.pin_config["SECURITY"] = self.default_values
        self.save_pin_file()
        self.logger.debug("Pin reseted")

    def read_pin_file(self):
        self.logger.debug("Read Pin from file")
        # Check if .ini file exists and if security options are valid.
        file_values = self.default_values
        try:
            self.logger.debug("Start reading pin config...")
            dataset = self.pin_config.read(self.pin_file)
            self.logger.debug(f"Pin config read.")
        except (ParsingError, MissingSectionHeaderError) as ex:
            self.logger.debug(f"Read Pin failed: {ex}")
            self.reset_pin_file()
            dataset = self.pin_config.read(self.pin_file)

        self.logger.debug(f"pin file: {self.pin_file}, dataset: {dataset}")

        if self.pin_file in dataset:
            try:
                file_values["DEFAULT_PIN"] = self.pin_config['SECURITY'].get('DEFAULT_PIN')
                file_values["USE_PIN_LOCK"] = self.pin_config['SECURITY'].getboolean('USE_PIN_LOCK')
                return file_values
            except (ValueError, KeyError) as ex:
                self.logger.debug(f"Pin dataset failed: {ex}")
                self.reset_pin_file()
                return file_values
        else:
            self.logger.debug(f"Pin file is not in dataset.")
            self.reset_pin_file()
        self.logger.debug("Pin read from file")
        return file_values

    def validate_pin(self, pin):
        return bool(re.fullmatch(r"\d{4,8}", pin))

    def is_safe_url(self, target):
        ref_url = urlparse(request.host_url)
        test_url = urlparse(urljoin(request.host_url, target))
        return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

    def first_call(self):
        self.logger.debug("Enter first_call")
        if USE_PIN_LOCK:
            self.logger.debug("Logout User")
            logout_user()

    def set_pin_setting(self, data):
        self.logger.debug("Enter set_pin_setting()")
        self.pin_config["SECURITY"] = data
        self.save_pin_file()

    def get_pin_setting(self):
        self.logger.debug("Enter get_pin_setting()")
        return self.read_pin_file()

    def reset_pin_settings(self, data):
        self.logger.debug("Enter reset_pin_settings()")
        self.pin_config["SECURITY"] = data
        self.save_pin_file()
        return self.read_pin_file()

    def login(self):
        self.logger.debug("Enter login()")
        user = User()
        login_user(user)

    def get_use_pin_lock(self):
        self.logger.debug("Enter get_use_pin_lock()")
        return USE_PIN_LOCK


class User(UserMixin):
    id = 1001
