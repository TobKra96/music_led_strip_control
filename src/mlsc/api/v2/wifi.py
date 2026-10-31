from typing import Literal

from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field

from mlsc.api.v2.errors import READ_ERRORS, Problem, ProblemError
from mlsc.api.v2.security import api_login_required
from mlsc.webserver.executer import Executer
from mlsc.webserver.messages import WifiChangeFailed, WifiUnsupported
from mlsc.wifi import WifiError, WifiManager
from mlsc.wifi.supervisor import WifiSupervisor

tag = Tag(name="Wi-Fi", description="Join a network, forget one, or raise the Hotspot")
wifi_api = APIBlueprint("wifi_api_v2", __name__, url_prefix="/api/v2/wifi", abp_tags=[tag])

CHANGE_ERRORS = {"401": Problem, "415": Problem, "422": Problem, "503": Problem}


class HotspotOut(BaseModel):
    ssid: str
    password: str | None = Field(description="Shown to an authenticated session, or to anyone while the PIN lock is off.")
    address: str | None = Field(default=None, description="The IPv4 address the running Hotspot answers on. `null` when it cannot be read.")


class DiagnosisOut(BaseModel):
    status: str = Field(description="`ok` or `warning`.")
    message: str
    suggested_fix: str | None


class WifiStatusOut(BaseModel):
    supported: bool = Field(description="`false` without NetworkManager (Windows, WSL, other Linux): the panel is hidden or says so.")
    hotspot_supported: bool = Field(description="Whether the adapter can run a Hotspot.")
    country: str | None = Field(description="The Wi-Fi country, `null` when it is not set.")
    interface: str | None = Field(description="The Wi-Fi Adapter MLSC works with. The configured one when it is missing, `null` when there is none.")
    radio: str = Field(description="The state of the Wi-Fi Radio: `ready`, `switched_off`, `blocked`, `unavailable` or `no_adapter`.")
    diagnosis: DiagnosisOut = Field(description="What to tell the user about the Wi-Fi. The banner text of the page.")
    mode: str = Field(description="`client` or `hotspot`.")
    connected: bool
    ssid: str | None = Field(description="The network the Pi is connected to.")
    ip: str | None
    hotspot: HotspotOut | None = Field(description="Set while the Hotspot is up.")


class NetworkOut(BaseModel):
    ssid: str
    signal: int = Field(description="Signal strength, 0 to 100.")
    security: str | None = Field(description="`null` for an open network.")
    in_use: bool
    known: bool = Field(description="Whether the network is saved. Saved passwords are never returned.")


class NetworksOut(BaseModel):
    networks: list[NetworkOut]


class ConnectBody(BaseModel):
    ssid: str = Field(min_length=1, max_length=32)
    password: str | None = Field(default=None, max_length=63, description="Handed to NetworkManager and never stored by MLSC.")


class ForgetBody(BaseModel):
    ssid: str = Field(min_length=1, max_length=32)


class RadioBody(BaseModel):
    enabled: Literal[True] = Field(description="Only switching the radio on is possible: switching it off could cut off the user.")


class HotspotBody(BaseModel):
    enabled: bool
    ssid: str | None = Field(default=None, min_length=1, max_length=32, description="Generated when left out.")
    password: str | None = Field(default=None, min_length=8, max_length=63, description="Generated when left out.")
    ip: str | None = Field(default=None, max_length=15, description=(
        "The Hotspot's IPv4 address, saved with the Hotspot settings (netmask `/24`). A private address (`10/8`, `172.16/12`, `192.168/16`) "
        "that is not a network or broadcast address and does not overlap a network the Pi is connected to. "
        "Empty means the default `10.42.0.1`; left out keeps the saved one."))


def _wifi() -> WifiManager:
    return Executer.instance.wifi_manager


def _supervisor() -> WifiSupervisor:
    return Executer.instance.wifi_supervisor


def _require_supported() -> WifiManager:
    wifi = _wifi()
    if not wifi.capabilities().supported:
        raise ProblemError(WifiUnsupported)
    return wifi


def _status() -> dict:
    wifi = _wifi()
    capabilities, status = wifi.capabilities(), wifi.status()
    hotspot = {"ssid": status.hotspot.ssid, "password": status.hotspot.password, "address": status.hotspot.address} if status.hotspot else None
    diagnosis = wifi.diagnose()
    return {
        "supported": capabilities.supported, "hotspot_supported": capabilities.hotspot, "country": capabilities.country,
        "interface": capabilities.interface, "radio": capabilities.radio,
        "diagnosis": {"status": diagnosis.status.value, "message": diagnosis.message, "suggested_fix": diagnosis.suggested_fix},
        "mode": status.mode, "connected": status.connected, "ssid": status.ssid, "ip": status.ip, "hotspot": hotspot,
    }


def _change(action) -> dict:
    try:
        action()
    except WifiError as e:
        raise ProblemError(WifiChangeFailed, str(e)) from e
    return _status()


@wifi_api.get("/status", summary="Get the Wi-Fi status", responses={"200": WifiStatusOut, "401": Problem})
@api_login_required
def get_status():
    """Always answers, also on a host without NetworkManager, where `supported` is `false`."""
    return _status()


@wifi_api.get("/scan", summary="Scan for Wi-Fi networks", responses={"200": NetworksOut, **READ_ERRORS, "503": Problem})
@api_login_required
def scan():
    networks = _require_supported().scan()
    return {"networks": [{"ssid": n.ssid, "signal": n.signal, "security": n.security, "in_use": n.in_use, "known": n.known} for n in networks]}


@wifi_api.post("/connect", summary="Join a Wi-Fi network", responses={"200": WifiStatusOut, **CHANGE_ERRORS})
@api_login_required
def connect(body: ConnectBody):
    """The connection is saved by the system under the SSID. A wrong password is a `422` and leaves nothing saved.

    The change is tracked as an `operation` event of kind `wifi`: `pending` until a connection with an IP is proven, then `confirmed`,
    or `rolled_back` after 45 seconds without one. `wifi.state` events follow the mode and connection.
    """
    _require_supported()
    return _change(lambda: _supervisor().connect(body.ssid, body.password))


@wifi_api.post("/forget", summary="Forget a saved Wi-Fi network", responses={"204": None, **CHANGE_ERRORS})
@api_login_required
def forget(body: ForgetBody):
    wifi = _require_supported()

    def forget_when_ready() -> None:
        wifi.require_ready()
        wifi.forget(body.ssid)

    _change(forget_when_ready)
    return "", 204


@wifi_api.put("/hotspot", summary="Switch the Hotspot on or off", responses={"200": WifiStatusOut, **CHANGE_ERRORS})
@api_login_required
def put_hotspot(body: HotspotBody):
    """On saves the Hotspot as the mode and drops a client connection. Off returns to the saved networks.

    A change that does not end in a working connection within 45 seconds is rolled back to the previous mode.
    A new address is rejected with a `422` naming the problem, such as the connected network it overlaps. Changing the address
    of a Hotspot that a phone is using is only confirmed once a phone is connected again, otherwise it is rolled back to the previous address.
    It is tracked as an `operation` event of kind `wifi`, and `wifi.state` events follow the mode and fallback.
    """
    _require_supported()
    return _change(lambda: _supervisor().set_hotspot(body.enabled, body.ssid, body.password, body.ip))



@wifi_api.put("/radio", summary="Switch the Wi-Fi on", responses={"200": WifiStatusOut, **CHANGE_ERRORS})
@api_login_required
def put_radio(body: RadioBody):  # ruff: ignore[unused-function-argument]
    """Only possible while the radio is `switched_off`; the other states are rejected with the message of the state.

    Waits up to about 10 seconds for the adapter to come up and answers with the new status. There is no off:
    it would cut off a user who reached the page over Wi-Fi.
    """
    wifi = _require_supported()
    return _change(wifi.enable_radio)
