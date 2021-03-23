
"""
Copyright (c) 2019 - present AppSeed.us
"""

from importlib import import_module
from flask import Flask


def register_blueprints(app):
    for module_name in ('base', 'home'):
        module = import_module('libs.app.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)


def create_app():
    app = Flask(__name__, static_folder='base/static')
    register_blueprints(app)
    return app
