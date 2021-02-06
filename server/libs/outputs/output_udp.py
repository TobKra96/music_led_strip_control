from libs.outputs.output import Output  # pylint: disable=E0611, E0401
from time import sleep
import numpy as np
import socket


class OutputUDP(Output):
    def __init__(self, device):
        # Call the constructor of the base class.
        super(OutputUDP, self).__init__(device)

        output_id = "output_udp"

        self._udp_client_ip = self._device_config["output"][output_id]["UDP_Client_IP"]
        self._udp_client_port = int(self._device_config["output"][output_id]["UDP_Client_Port"])
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def show(self, output_array):
        # Typecast the array to int.
        output_array = output_array.clip(0, 255).astype(np.uint8)
        byte_array = output_array.tobytes('F')
        self._sock.sendto(byte_array, (self._udp_client_ip, self._udp_client_port))
