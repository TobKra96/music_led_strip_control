import socket, pickle, struct
from time import sleep
import time
from subprocess import check_output
import sys

class ServerService:

    def start(self, config_lock, notification_queue_in, notification_queue_out, server_queue, server_queue_lock):
        self._config_lock = config_lock
        self._notification_queue_in = notification_queue_in
        self._notification_queue_out = notification_queue_out
        self._server_queue = server_queue
        self._server_queue_lock = server_queue_lock

        ten_seconds_counter = time.time()
        start_time = time.time()
        
        self._frame_counter = 0
        while True:
            print("--- Try to connect with the server. ---")

            try:

                hostIP = socket.gethostbyname("raspi-led")
                port = 65432
                print("Connect to " + str(hostIP) + ":" + str(port))

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.connect((hostIP, port))

                    while True:
                        output_array = None

                        
                        self._server_queue_lock.acquire()
                        if not self._server_queue.empty():
                            output_array = self._server_queue.get()
                        self._server_queue_lock.release()

                        if output_array is None:
                            #print("Server Service | Output array is empty")
                            continue

                        self.sendArray(sock, output_array)


                        

                        end_time = time.time()
                        
                        if time.time() - ten_seconds_counter > 10:
                            ten_seconds_counter = time.time()
                            time_dif = end_time - start_time
                            fps = 1 / time_dif
                            print("Server Service | FPS: " + str(fps))

                        start_time = time.time()
                        
            
            except TimeoutError as ex:
                print("Connection timed out.")
            
            except:
                print("Unexpected error in server service:" + str(sys.exc_info()[0]))

            sleep(10)

    def sendArray(self, sock, array):

        # Send Array Data
        sendData = pickle.dumps(array)
        self.send_msg(sock, sendData)


    def send_msg(self, sock, msg):
        # Prefix each message with a 4-byte length (network byte order)
        msg = struct.pack('>I', len(msg)) + msg
        sock.sendall(msg)