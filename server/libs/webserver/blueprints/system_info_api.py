from libs.webserver.executer import Executer

from flask_login import login_required
from flask import Blueprint, jsonify

system_info_api = Blueprint('system_info_api', __name__)


@system_info_api.get('/api/system/performance')
@login_required
def get_performance():  # pylint: disable=E0211
    """
    System performance
    ---
    tags:
      - System
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                system:
                  cpu_info:
                    frequency: num
                    percent: num
                  disk_info:
                    free: int
                    percent: num
                    total: int
                    used: int
                  memory_info:
                    available: int
                    free: int
                    percent: num
                    total: int
                    used: int
                  network_info:
                    - address: str
                      bytes_recv: int
                      bytes_sent: int
                      name: str
                      netmask: str
              type: object
      "403":
        description: Could not find data value
    """
    result = Executer.instance.system_info_executer.get_system_info_performance()

    if result is None:
        return "Could not find data value.", 403

    data_out = dict()
    data_out["system"] = result
    return jsonify(data_out)


@system_info_api.get('/api/system/temperature')
@login_required
def get_temperature():  # pylint: disable=E0211
    """
    Raspberry Pi temperature
    ---
    tags:
      - System
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                system:
                  raspi:
                    celsius: num
                    fahrenheit: num
              type: object
      "403":
        description: Could not find data value
    """
    result = Executer.instance.system_info_executer.get_system_info_temperature()

    if result is None:
        return "Could not find data value.", 403

    data_out = dict()
    data_out["system"] = result
    return jsonify(data_out)


@system_info_api.get('/api/system/services')
@login_required
def get_services():  # pylint: disable=E0211
    """
    System services
    ---
    tags:
      - System
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                services:
                  - str
              type: object
      "403":
        description: Could not find data value
    """
    result = Executer.instance.system_info_executer.get_services()

    if result is None:
        return "Could not find data value.", 403

    data_out = dict()
    data_out["services"] = result
    return jsonify(data_out)


@system_info_api.get('/api/system/services/status')
@login_required
def get_services_status():  # pylint: disable=E0211
    """
    System services status
    ---
    tags:
      - System
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                services:
                  - name: str
                    not_found: bool
                    running: bool
                    status: int
              type: object
      "403":
        description: Could not find data value
    """
    result = Executer.instance.system_info_executer.get_system_info_services()

    if result is None:
        return "Could not find data value.", 403

    data_out = dict()
    data_out["services"] = result
    return jsonify(data_out)


@system_info_api.get('/api/system/devices/status')
@login_required
def get_devices_status():  # pylint: disable=E0211
    """
    Devices status
    ---
    tags:
      - System
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                devices:
                  - connected: bool
                    id: str
                    name: str
              type: object
      "403":
        description: Could not find data value
    """
    result = Executer.instance.system_info_executer.get_system_info_device_status()

    if result is None:
        return "Could not find data value.", 403

    data_out = dict()
    data_out["devices"] = result
    return jsonify(data_out)


@system_info_api.get('/api/system/version')
@login_required
def get_version():  # pylint: disable=E0211
    """
    System version
    ---
    tags:
      - System
    responses:
      "200":
        description: OK
        content:
          application/json:
            schema:
              example:
                versions:
                  - name: str
                    version: str
              type: object
      "403":
        description: Could not find data value
    """
    result = Executer.instance.system_info_executer.get_system_version()

    if result is None:
        return "Could not find data value.", 403

    data_out = dict()
    data_out["versions"] = result
    return jsonify(data_out)
