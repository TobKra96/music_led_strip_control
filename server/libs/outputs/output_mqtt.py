from libs.outputs.output import Output # pylint: disable=E0611, E0401
from time import sleep
import paho.mqtt.publish as publish
import numpy as np
import socket

class OutputMptt(Output):
    def __init__(self, device):

        # Call the constructor of the base class.
        super(OutputMptt, self).__init__(device)

        output_id = "output_udp"
        #self._mqtt_broker = self._device_config["output"][output_id]["MQTT_Broker"]
        #self._mqtt_path = self._device_config["output"][output_id]["MQTT_Path"]

        self._udp_client_ip = self._device_config["output"][output_id]["UDP_Client_IP"]
        self._udp_client_port = int(self._device_config["output"][output_id]["UDP_Client_Port"])
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def show(self, output_array):

        # Typecast the array to int
        output_array = output_array.clip(0, 255).astype(np.uint8)
        
        # sort the colors. grb
        #g = np.left_shift(output_array[1][:].astype(int), 16) # pylint: disable=assignment-from-no-return
        #r = np.left_shift(output_array[0][:].astype(int), 8) # pylint: disable=assignment-from-no-return    
        #b = output_array[2][:].astype(int)
        #rgb = np.bitwise_or(np.bitwise_or(r, g), b).astype(int)

        #print(output_array.tostring())
        byte_array = output_array.tobytes('F')
        #print(len(byte_array))
        #print(byte_array)
        #byte_array = bytearray([11, 11, 12, 51, 21, 31, 31, 12])
        #sleep(0.05)

        self._sock.sendto(byte_array, (self._udp_client_ip, self._udp_client_port))
    

        #publish.single(self._mqtt_path, byte_array , hostname=self._mqtt_broker)