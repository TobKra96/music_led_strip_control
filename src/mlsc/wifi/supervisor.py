"""The Setup Fallback and the Wi-Fi Rollback: the timed decisions on top of a WifiManager.

`tick()` makes every decision from the injected clock, so tests drive it with a fake one.
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Protocol

from loguru import logger

from mlsc.wifi.credentials import HotspotCredentials
from mlsc.wifi.manager import CLIENT, HOTSPOT, WifiError, WifiManager, WifiStatus

BOOT_FALLBACK_SECONDS = 60
LOST_FALLBACK_SECONDS = 300
RETRY_INTERVAL_SECONDS = 120
RETRY_GRACE_SECONDS = 20
ROLLBACK_SECONDS = 45
TICK_SECONDS = 5


class WifiSettings(Protocol):
    mode: str
    setup_fallback: bool


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


@dataclass(frozen=True)
class _Pending:
    """A change waiting for proof that it works, and what to return to if it does not."""

    target: str
    deadline: float
    mode: str
    fallback: bool
    status: WifiStatus


def _working(status: WifiStatus) -> bool:
    return status.connected and bool(status.ip)


class WifiSupervisor:
    def __init__(self, manager: WifiManager, settings: WifiSettings, clock: Callable[[], float],
                 ethernet_up: Callable[[], bool], credentials: HotspotCredentials) -> None:
        self._manager = manager
        self._settings = settings
        self._clock = clock
        self._ethernet_up = ethernet_up
        self._credentials = credentials
        self._lock = threading.RLock()
        self._lost_since: float | None = clock()
        self._ever_connected = False
        self._pending: _Pending | None = None
        self._retry_at = 0.0
        self._retry_deadline: float | None = None
        self.fallback_active = False

    def connect(self, ssid: str, password: str | None) -> None:
        """Join a network. If that does not end in a connection with an IP within the Rollback time, go back to the previous mode."""
        self._apply(lambda: self._manager.connect(ssid, password), CLIENT)

    def set_hotspot(self, enabled: bool, ssid: str | None = None, password: str | None = None) -> None:
        """Save the Hotspot as the Wi-Fi mode (or return to client mode). A missing SSID or password comes from the credentials."""
        if enabled:
            self._apply(lambda: self._manager.start_hotspot(ssid or self._credentials.ssid(), password or self._credentials.password()), HOTSPOT)
        else:
            self._apply(self._manager.stop_hotspot, CLIENT)

    def tick(self) -> None:
        with self._lock:
            self._check_rollback()
            if self._pending is None:
                self._supervise_fallback()

    def run_forever(self, stop: threading.Event, interval: float = TICK_SECONDS) -> None:
        while not stop.wait(interval):
            try:
                self.tick()
            except Exception:
                logger.exception("The Wi-Fi supervisor failed.")

    def _apply(self, change: Callable[[], None], target: str) -> None:
        with self._lock:
            before = self._pending or _Pending(target, 0.0, self._settings.mode, self.fallback_active, self._manager.status())
            before = replace(before, target=target, deadline=self._clock() + ROLLBACK_SECONDS)
            try:
                change()
            except WifiError:
                self._revert_if_changed(before)
                raise
            self._settings.mode = target
            self.fallback_active = False
            self._retry_deadline = None
            self._pending = before

    def _check_rollback(self) -> None:
        pending = self._pending
        if pending is None:
            return
        status = self._manager.status()
        if status.mode == pending.target and (pending.target == HOTSPOT or _working(status) or self._ethernet_up()):
            self._pending = None
            self._ever_connected = self._ever_connected or pending.target == CLIENT
            self._lost_since = None
        elif self._clock() >= pending.deadline:
            self._pending = None
            logger.warning("The Wi-Fi change did not result in a connection; returning to the {} mode.", pending.mode)
            self._revert(pending)

    def _revert_if_changed(self, before: _Pending) -> None:
        now = self._manager.status()
        if (now.mode, now.connected, now.ssid) != (before.status.mode, before.status.connected, before.status.ssid):
            self._revert(before)

    def _revert(self, before: _Pending) -> None:
        self._settings.mode = before.mode
        self._lost_since = None
        try:
            if before.status.mode == HOTSPOT:
                self._manager.start_hotspot(self._credentials.ssid(), self._credentials.password())
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
            self._manager.start_hotspot(self._credentials.ssid(), self._credentials.password())
        except WifiError as e:
            logger.warning("The Hotspot could not be raised: {}", e)

    def _raise_fallback(self) -> None:
        try:
            self._manager.start_hotspot(self._credentials.ssid(), self._credentials.password())
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
