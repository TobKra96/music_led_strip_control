from libs.outputs.output import Output  # pylint: disable=E0611, E0401
import numpy as np
import socket
import logging


class OutputUDP(Output):
    def __init__(self, device):
        # Call the constructor of the base class.
        super(OutputUDP, self).__init__(device)
        self.logger = logging.getLogger(__name__)

        output_id = "output_udp"

        self._udp_client_ip = self._device_config["output"][output_id]["UDP_Client_IP"]
        self._udp_client_port = int(self._device_config["output"][output_id]["UDP_Client_Port"])
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def show(self, output_array):
        # Typecast the array to int.
        output_array = output_array.clip(0, 255).astype(np.uint8)
        byte_array = output_array.tobytes('F')
        try:
            self._sock.sendto(byte_array, (self._udp_client_ip, self._udp_client_port))
        except Exception as ex:
            self.logger.exception(f"Could not send to client", ex)
            self.logger.debug(f"Reinit output of {self._udp_client_ip}")
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
