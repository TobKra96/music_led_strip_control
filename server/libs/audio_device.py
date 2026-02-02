class AudioDevice:

    def __init__(self, device_id, name, default_sample_rate) -> None:
        self.device_id = device_id
        self.name = name
        self.default_sample_rate = default_sample_rate

    def to_string(self):
        return f"{self.device_id} - {self.name} - {self.default_sample_rate} Hz"
