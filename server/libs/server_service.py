import socket, pickle, struct
from time import sleep
import time
from subprocess import check_output

class ServerService:

    def start(self, config_lock, notification_queue_in, notification_queue_out, server_queue, server_queue_lock):
        self._config_lock = config_lock
        self._notification_queue_in = notification_queue_in
        self._notification_queue_out = notification_queue_out
        self._server_queue = server_queue
        self._server_queue_lock = server_queue_lock

        ten_seconds_counter = time.time()
        start_time = time.time()

        self._lost_arrays_counter = 0
        while True:
            
            hostIP = self.my_ip()
            port = 65432
            print("Server listen to " + str(hostIP) + ":" + str(port))

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((hostIP, port))
                sock.listen()
                conn, addr = sock.accept()
                with conn:
                    while True:
                        # print("Get a new array")
                        # Get every time a new array.
                        try:
                            output_array = pickle.loads(self.recv_msg(conn))
                        except:
                            break

                        # Put it into the server_queue
                        self._server_queue_lock.acquire()
                        if self._server_queue.full():
                            #print("Server queue is full")
                            old_output_array = self._server_queue.get()
                            self._lost_arrays_counter = self._lost_arrays_counter + 1
                        self._server_queue.put(output_array)
                        self._server_queue_lock.release()


                        end_time = time.time()
                        
                        if time.time() - ten_seconds_counter > 10:
                            ten_seconds_counter = time.time()
                            time_dif = end_time - start_time
                            fps = 1 / time_dif
                            print("Server Service | FPS: " + str(fps))

                        start_time = time.time()

    # Thanks to kasperd
    # https://serverfault.com/questions/690391/finding-local-ip-addresses-using-pythons-stdlib-under-debian-jessie
    def my_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('192.0.0.8', 1027))
        except socket.error:
            return None
        return s.getsockname()[0]

    def recv_msg(self, conn):
        # Read message length and unpack it into an integer
        raw_msglen = self.recvall(conn, 4)
        if not raw_msglen:
            return None
        msglen = struct.unpack('>I', raw_msglen)[0]
        # print("Message lenght" + str(msglen))
        # Read the message data
        return self.recvall(conn, msglen)

    def recvall(self, conn, n):
        # Helper function to recv n bytes or return None if EOF is hit
        data = b''
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data