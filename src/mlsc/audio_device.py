MONITOR_MARKERS = ("monitor", "loopback", "stereo mix", "what u hear")


class AudioDevice:

    def __init__(self, device_id, name, default_sample_rate, host_api="") -> None:
        self.device_id = device_id
        self.name = name
        self.default_sample_rate = default_sample_rate
        self.host_api = host_api

    @property
    def is_monitor(self) -> bool:
        """Whether this is a Monitor Device: it carries played or remote audio rather than a microphone."""
        name = self.name.lower()
        return any(marker in name for marker in MONITOR_MARKERS)

    def matches(self, name: str | None, host_api: str | None) -> bool:
        """Whether this is the device stored as `name` and `host_api`. No stored host API matches any."""
        return self.name == name and (host_api is None or self.host_api == host_api)

    def to_string(self):
        return f"{self.device_id} - {self.name} - {self.default_sample_rate} Hz"
