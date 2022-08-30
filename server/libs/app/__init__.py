
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask import Flask, render_template
from importlib import import_module


def register_blueprints(app):
    for module_name in ('base', 'home'):
        module = import_module('libs.app.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)


def page_not_found(_):
    return render_template('page-404.html'), 404


def server_error(_):
    return render_template('page-500.html'), 500


def register_errors(app):
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, server_error)


def create_app():
    app = Flask(__name__, static_folder='base/static')
    register_blueprints(app)
    register_errors(app)
    return app
