import socket

import numpy as np
from loguru import logger

from mlsc.diagnosis import Diagnosis
from mlsc.outputs.output import Output
from mlsc.strip import udp_channel_order


class OutputUDP(Output):
    def __init__(self, device) -> None:
        # Call the constructor of the base class.
        super().__init__(device)
        output_id = "output_udp"

        self._udp_client_ip = self._device_config["output"][output_id]["udp_client_ip"]
        self._udp_client_port = int(self._device_config["output"][output_id]["udp_client_port"])
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._channel_order = udp_channel_order(self._device_config["chip_family"], self._device_config["colour_order"])
        self._led_brightness = int(self._device_config["led_brightness"])  # Set to '0' for darkest and 100 for brightest.

    def show(self, output_array):

        output_array = (output_array * self._led_brightness / 100)

        output_array = self.map_channels(output_array)
        # Typecast the array to int.
        output_array = output_array.clip(0, 255).astype(np.uint8)

        byte_array = output_array.tobytes("F")
        try:
            self._sock.sendto(byte_array, (self._udp_client_ip, self._udp_client_port))
        except Exception as ex:
            logger.exception(f"Could not send to client: {ex}")
            logger.debug(f"Reinit output of {self._udp_client_ip}")
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def map_channels(self, output_array_in):
        output_array_out = output_array_in.copy()
        if len(output_array_in) >= 3:
            output_array_out[:3] = output_array_in[list(self._channel_order)]
        return output_array_out

    @classmethod
    def diagnose(cls, device_config: dict, host=None) -> Diagnosis:
        """Checks the host and port only: UDP has no acknowledgement, so delivery cannot be verified."""
        settings = device_config["output"]["output_udp"]
        ip, port = settings["udp_client_ip"], settings["udp_client_port"]
        if not ip or not isinstance(ip, str):
            return Diagnosis.error("No UDP client host is set.", "Enter the host name or IP address of the UDP client.")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            return Diagnosis.error(f"The UDP port {port} is not valid.", "Use a port between 1 and 65535.")
        try:
            socket.getaddrinfo(ip, port, type=socket.SOCK_DGRAM)
        except OSError as e:
            message = f"The UDP client host {ip!r} cannot be resolved ({e})."
            return Diagnosis.error(message, "Check the host name or use the IP address of the client.")
        return Diagnosis.ok(f"Sending to {ip}:{port}. UDP has no acknowledgement, so delivery is not verified.")
