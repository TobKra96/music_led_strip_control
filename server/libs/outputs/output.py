class Output:
    def __init__(self, device) -> None:
        self._device = device
        self._device_config = device.device_config

    def show(self, output_array):
        msg = "Please implement this method."
        raise NotImplementedError(msg)
