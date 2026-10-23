from flask import jsonify
from flask_openapi3 import APIBlueprint

from mlsc.webserver.auth import login_required
from mlsc.webserver.executer import Executer
from mlsc.webserver.openapi_docs import doc

system_info_api = APIBlueprint("system_info_api", __name__)


@system_info_api.get("/api/system/performance", **doc("system_info_api/get_performance.yml"))
@login_required
def get_performance():
    data_out = Executer.instance.system_info_executer.get_system_info_performance()

    return jsonify(data_out)


@system_info_api.get("/api/system/temperature", **doc("system_info_api/get_temperature.yml"))
@login_required
def get_temperature():
    data_out = Executer.instance.system_info_executer.get_system_info_temperature()

    return jsonify(data_out)


@system_info_api.get("/api/system/services", **doc("system_info_api/get_services.yml"))
@login_required
def get_services():
    data_out = Executer.instance.system_info_executer.get_services()

    return jsonify(data_out)


@system_info_api.get("/api/system/services/status", **doc("system_info_api/get_services_status.yml"))
@login_required
def get_services_status():
    data_out = Executer.instance.system_info_executer.get_system_info_services()

    return jsonify(data_out)


@system_info_api.get("/api/system/devices/status", **doc("system_info_api/get_devices_status.yml"))
@login_required
def get_devices_status():
    data_out = Executer.instance.system_info_executer.get_system_info_device_status()

    return jsonify(data_out)


@system_info_api.get("/api/system/version", **doc("system_info_api/get_version.yml"))
@login_required
def get_version():
    data_out = Executer.instance.system_info_executer.get_system_version()

    return jsonify(data_out)
