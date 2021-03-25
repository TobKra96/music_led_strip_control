# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask import render_template
from libs.app.base import blueprint


# Errors
@blueprint.errorhandler(404)
def not_found_error():
    return render_template('page-404.html'), 404


@blueprint.errorhandler(500)
def internal_error():
    return render_template('page-500.html'), 500
