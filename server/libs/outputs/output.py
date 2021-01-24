class Output:
    def __init__(self, device):
        self._device = device
        self._device_config = device.device_config

    def show(self, output_array):
        raise NotImplementedError("Please Implement this method")