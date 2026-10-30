from mlsc.diagnosis import Diagnosis


class Output:
    def __init__(self, device) -> None:
        self._device = device
        self._device_config = device.device_config

    @staticmethod
    def show(output_array) -> None:
        msg = f"Please implement this method. {output_array}"
        raise NotImplementedError(msg)

    @classmethod
    def diagnose(cls, device_config: dict, host=None) -> Diagnosis:
        """Check that this Output can work with `device_config`, without creating it."""
        return Diagnosis.ok("Ready.")
