"""The Setup Fallback and the Wi-Fi Rollback: the timed decisions on top of a WifiManager.

`tick()` makes every decision from the injected clock, so tests drive it with a fake one.
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Protocol

from loguru import logger

from mlsc.operations import Operation, OperationRegistry, OperationState
from mlsc.wifi.credentials import HotspotCredentials
from mlsc.wifi.hotspot_address import DEFAULT_HOTSPOT_ADDRESS, clashing_network, validate_hotspot_address
from mlsc.wifi.manager import CLIENT, HOTSPOT, RADIO_READY, WifiError, WifiManager, WifiStatus

BOOT_FALLBACK_SECONDS = 60
LOST_FALLBACK_SECONDS = 300
RETRY_INTERVAL_SECONDS = 120
RETRY_GRACE_SECONDS = 20
ROLLBACK_SECONDS = 45
TICK_SECONDS = 5


class WifiSettings(Protocol):
    mode: str
    setup_fallback: bool
    hotspot_ip: str


class ConfigWifiSettings:
    """The `wifi` section of the config as WifiSettings. Setting the mode saves it."""

    def __init__(self, config_service) -> None:
        self._config_service = config_service

    @property
    def mode(self) -> str:
        return self._config_service.config["wifi"]["mode"]

    @mode.setter
    def mode(self, mode: str) -> None:
        self._config_service.config["wifi"]["mode"] = mode
        self._config_service.save_config()

    @property
    def setup_fallback(self) -> bool:
        return self._config_service.config["wifi"]["setup_fallback"]

    @property
    def hotspot_ip(self) -> str:
        return self._config_service.config["wifi"].get("hotspot_ip", "")

    @hotspot_ip.setter
    def hotspot_ip(self, address: str) -> None:
        self._config_service.config["wifi"]["hotspot_ip"] = address
        self._config_service.save_config()


@dataclass(frozen=True)
class _Pending:
    """A change waiting for proof that it works, and what to return to if it does not."""

    target: str
    deadline: float
    mode: str
    fallback: bool
    status: WifiStatus
    hotspot_ip: str = ""
    needs_client: bool = False
    operation: Operation | None = None


def _working(status: WifiStatus) -> bool:
    return status.connected and bool(status.ip)


class WifiSupervisor:
    def __init__(self, manager: WifiManager, settings: WifiSettings, clock: Callable[[], float],
                 ethernet_up: Callable[[], bool], credentials: HotspotCredentials,
                 operations: OperationRegistry | None = None, publish: Callable[[str, dict], None] | None = None) -> None:
        self._manager = manager
        self._settings = settings
        self._clock = clock
        self._ethernet_up = ethernet_up
        self._credentials = credentials
        self._operations = operations
        self._publish = publish
        self._published_state: dict | None = None
        self._lock = threading.RLock()
        self._lost_since: float | None = clock()
        self._ever_connected = False
        self._pending: _Pending | None = None
        self._retry_at = 0.0
        self._retry_deadline: float | None = None
        self.fallback_active = False

    def connect(self, ssid: str, password: str | None) -> None:
        """Join a network. If that does not end in a connection with an IP within the Rollback time, go back to the previous mode."""
        self._manager.require_ready()
        self._apply(lambda: self._manager.connect(ssid, password), CLIENT)

    def set_hotspot(self, enabled: bool, ssid: str | None = None, password: str | None = None, ip: str | None = None) -> None:
        """Save the Hotspot as the Wi-Fi mode (or return to client mode). A missing SSID or password comes from the credentials.

        `ip` is the Hotspot's address: None keeps the saved one, an empty string goes back to the default.
        """
        self._manager.require_ready()
        if enabled:
            if ip:
                validate_hotspot_address(ip, self._manager.connected_networks())
            address = self._settings.hotspot_ip if ip is None else ip
            self._apply(lambda: self._manager.start_hotspot(
                ssid or self._credentials.ssid(), password or self._credentials.password(), self._hotspot_address(address)), HOTSPOT, address)
        else:
            self._apply(self._manager.stop_hotspot, CLIENT)

    def tick(self) -> None:
        with self._lock:
            if self._manager.radio() != RADIO_READY:
                # Nothing to supervise without a working radio; the timers start fresh when it returns.
                self._lost_since = None
                self._publish_state()
                return
            self._check_rollback()
            if self._pending is None:
                self._supervise_fallback()
            self._publish_state()

    def run_forever(self, stop: threading.Event, interval: float = TICK_SECONDS) -> None:
        while not stop.wait(interval):
            try:
                self.tick()
            except Exception:
                logger.exception("The Wi-Fi supervisor failed.")

    def _apply(self, change: Callable[[], None], target: str, hotspot_ip: str | None = None) -> None:
        with self._lock:
            status = self._manager.status()
            before = self._pending or _Pending(target, 0.0, self._settings.mode, self.fallback_active, status, self._settings.hotspot_ip)
            # A phone on the Hotspot is cut off by an address change: only a phone coming back proves the new Hotspot works.
            moves_hotspot = target == HOTSPOT and status.mode == HOTSPOT and status.hotspot is not None and (
                (self._hotspot_address(hotspot_ip) or DEFAULT_HOTSPOT_ADDRESS) != (status.hotspot.address or DEFAULT_HOTSPOT_ADDRESS))
            needs_client = before.needs_client or (moves_hotspot and self._manager.hotspot_clients() > 0)
            operation = self._operations.begin("wifi") if self._operations else None
            self._end(before.operation, OperationState.FAILED, "Replaced by a newer Wi-Fi change.")
            before = replace(before, target=target, deadline=self._clock() + ROLLBACK_SECONDS, needs_client=needs_client, operation=operation)
            try:
                change()
            except WifiError as e:
                reverted = self._revert_if_changed(before)
                self._end(operation, OperationState.ROLLED_BACK if reverted else OperationState.FAILED, str(e))
                self._publish_state()
                raise
            self._settings.mode = target
            if hotspot_ip is not None:
                self._settings.hotspot_ip = hotspot_ip
            self.fallback_active = False
            self._retry_deadline = None
            self._pending = before
            self._publish_state()

    def _check_rollback(self) -> None:
        pending = self._pending
        if pending is None:
            return
        status = self._manager.status()
        if status.mode == pending.target and self._proven(pending, status):
            self._pending = None
            self._ever_connected = self._ever_connected or pending.target == CLIENT
            self._lost_since = None
            self._end(pending.operation, OperationState.CONFIRMED)
        elif self._clock() >= pending.deadline:
            self._pending = None
            logger.warning("The Wi-Fi change did not result in a connection; returning to the {} mode.", pending.mode)
            self._revert(pending)
            self._end(pending.operation, OperationState.ROLLED_BACK, "The change did not result in a connection.")

    def _proven(self, pending: _Pending, status: WifiStatus) -> bool:
        if pending.target == HOTSPOT:
            return not pending.needs_client or self._manager.hotspot_clients() > 0
        return _working(status) or self._ethernet_up()

    def _hotspot_address(self, saved: str | None = None) -> str | None:
        """The address to raise the Hotspot on: None for the default. A saved address that clashes with a connected network now is skipped."""
        address = self._settings.hotspot_ip if saved is None else saved
        if not address or address == DEFAULT_HOTSPOT_ADDRESS:
            return None
        clash = clashing_network(address, self._manager.connected_networks())
        if clash:
            logger.warning("The Hotspot address {} overlaps the connected network {}; the default {} is used instead.", address, clash, DEFAULT_HOTSPOT_ADDRESS)
            return None
        return address

    def _start_hotspot(self, address: str | None = None) -> None:
        self._manager.start_hotspot(self._credentials.ssid(), self._credentials.password(), self._hotspot_address(address))

    def _end(self, operation: Operation | None, state: OperationState, error: str | None = None) -> None:
        if operation is not None and self._operations is not None:
            self._operations.resolve(operation, state, error)

    def _publish_state(self) -> None:
        """Publish `wifi.state` when the mode, the connection, the radio or the Setup Fallback changed since the last time."""
        if self._publish is None:
            return
        status = self._manager.status()
        state = {"mode": status.mode, "connected": status.connected, "fallback": self.fallback_active, "radio": self._manager.radio()}
        if state != self._published_state:
            self._published_state = state
            self._publish("wifi.state", state)

    def _revert_if_changed(self, before: _Pending) -> bool:
        now = self._manager.status()
        if (now.mode, now.connected, now.ssid) == (before.status.mode, before.status.connected, before.status.ssid):
            return False
        self._revert(before)
        return True

    def _revert(self, before: _Pending) -> None:
        self._settings.mode = before.mode
        self._settings.hotspot_ip = before.hotspot_ip
        self._lost_since = None
        try:
            if before.status.mode == HOTSPOT:
                self._start_hotspot()
                self.fallback_active = before.fallback
                self._schedule_retry()
                return
            self._manager.stop_hotspot()
            if before.status.ssid:
                self._manager.connect(before.status.ssid, None)
        except WifiError as e:
            logger.warning("Returning to the previous Wi-Fi mode failed: {}", e)

    def _schedule_retry(self) -> None:
        self._retry_at = self._clock() + RETRY_INTERVAL_SECONDS
        self._retry_deadline = None

    def _supervise_fallback(self) -> None:
        now = self._clock()
        status = self._manager.status()
        if self._settings.mode != CLIENT:
            self.fallback_active = False
            if status.mode != HOTSPOT and now >= self._retry_at:
                self._raise_saved_hotspot(now)
            return
        if self.fallback_active:
            if self._retry_deadline is not None:
                self._finish_retry(status, now)
                return
            if status.mode == HOTSPOT:
                self._maybe_retry(now)
                return
            self.fallback_active = False
        if self._ethernet_up() or _working(status):
            self._lost_since = None
            self._ever_connected = self._ever_connected or _working(status)
            return
        if not self._settings.setup_fallback:
            return
        if self._lost_since is None:
            self._lost_since = now
        if now - self._lost_since >= (LOST_FALLBACK_SECONDS if self._ever_connected else BOOT_FALLBACK_SECONDS):
            self._raise_fallback()

    def _raise_saved_hotspot(self, now: float) -> None:
        """The saved mode is the Hotspot but it is not up, as after a reboot."""
        self._retry_at = now + RETRY_INTERVAL_SECONDS
        try:
            self._start_hotspot()
        except WifiError as e:
            logger.warning("The Hotspot could not be raised: {}", e)

    def _raise_fallback(self) -> None:
        try:
            self._start_hotspot()
        except WifiError as e:
            logger.warning("The Setup Fallback could not be raised: {}", e)
            return
        logger.info("No Wi-Fi connection: the Setup Fallback Hotspot is up.")
        self.fallback_active = True
        self._lost_since = None
        self._schedule_retry()

    def _maybe_retry(self, now: float) -> None:
        """Try the known networks again, but never take the Hotspot away from a phone that is using it."""
        if now < self._retry_at or self._manager.hotspot_clients() > 0:
            return
        try:
            self._manager.stop_hotspot()
        except WifiError as e:
            logger.warning("Dropping the Setup Fallback for a retry failed: {}", e)
            return
        self._retry_deadline = now + RETRY_GRACE_SECONDS

    def _finish_retry(self, status: WifiStatus, now: float) -> None:
        if _working(status):
            logger.info("Connected to a known network: the Setup Fallback is dropped.")
            self.fallback_active = False
            self._retry_deadline = None
            self._ever_connected = True
            self._lost_since = None
        elif now >= (self._retry_deadline or 0):
            self._raise_fallback()
            if not self.fallback_active:
                self._schedule_retry()
