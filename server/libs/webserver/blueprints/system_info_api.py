from libs.webserver.executer import Executer

from flask import Blueprint, request, jsonify
from flask_login import login_required

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
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        system: {
                            cpu_info: {
                                frequency: float,
                                percent: float
                            },
                            disk_info: {
                                free: int,
                                percent: float,
                                total: int,
                                used: int
                            },
                            memory_info: {
                                available: int,
                                free: int,
                                percent: float,
                                total: int,
                                used: int
                            },
                            network_info: [
                                {
                                    address: str,
                                    bytes_recv: int,
                                    bytes_sent: int,
                                    name: str,
                                    netmask: str
                                },
                                ...
                            ]
                        }
                    }
        403:
            description: Could not find data value
    """
    data_out = dict()

    data = Executer.instance.system_info_executer.get_system_info_performance()
    data_out["system"] = data

    if data is None:
        return "Could not find data value: data", 403
    else:
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
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        system: {
                            raspi: {
                                celsius: float,
                                fahrenheit: float
                            }
                        }
                    }
        403:
            description: Could not find data value
    """
    data_out = dict()

    data = Executer.instance.system_info_executer.get_system_info_temperature()
    data_out["system"] = data

    if data is None:
        return "Could not find data value: data", 403
    else:
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
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        services: [
                            str,
                            ...
                        ]
                    }
        403:
            description: Could not find data value
    """
    data_out = dict()

    data = Executer.instance.system_info_executer.get_services()
    data_out["services"] = data

    if data is None:
        return "Could not find data value: data", 403
    else:
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
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        services: [
                            {
                                name: str,
                                not_found: bool,
                                running: bool,
                                status: int
                            },
                            ...
                        ]
                    }
        403:
            description: Could not find data value
    """
    data_out = dict()

    data = Executer.instance.system_info_executer.get_system_info_services()
    data_out["services"] = data

    if data is None:
        return "Could not find data value: data", 403
    else:
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
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        devices: [
                            {
                                connected: bool,
                                id: str,
                                name: str
                            },
                            ...
                        ]
                    }
        403:
            description: Could not find data value
    """
    data_out = dict()
    data = Executer.instance.system_info_executer.get_system_info_device_status()
    data_out["devices"] = data

    if data is None:
        return "Could not find data value: data", 403
    else:
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
        200:
            description: OK
            schema:
                type: object,
                example:
                    {
                        versions: [
                            {
                            name: str,
                            version: str
                            },
                            ...
                        ]
                    }
        403:
            description: Could not find data value
    """
    data_out = dict()
    data = Executer.instance.system_info_executer.get_system_version()
    data_out["versions"] = data

    if data is None:
        return "Could not find data value: data", 403
    else:
        return jsonify(data_out)
