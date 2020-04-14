import socket
import threading

import rally.common.protobuf_utils as protobuf_utils
from rally.common.status_information import StatusInformation
from rally.protocol import clientprotocol_pb2


class SubClientCommunicator(threading.Thread):
    def __init__(self, program_arguments, receiver=None, raw_receiver=None, pos_receiver=None, status_receiver=None, raw_pos_receiver=None, raw_status_receiver=None):
        threading.Thread.__init__(self)
        self.terminate = False
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind(("127.0.0.1", 0))
        self.receive_port = self.udp_sock.getsockname()[1]
        self.udp_sock.settimeout(1)
        self.client_port = program_arguments.port
        self.client_index = program_arguments.client_index
        self.receiver = receiver
        self.raw_receiver = raw_receiver
        self.pos_receiver = pos_receiver
        self.status_receiver = status_receiver
        self.raw_pos_receiver = raw_pos_receiver
        self.raw_status_receiver = raw_status_receiver
        self.status_information = None
        if receiver is not None or pos_receiver is not None or status_receiver is not None:
            self.status_information = StatusInformation()

    def run(self):
        # Register with the client
        client_to_server = clientprotocol_pb2.ClientToServer()
        client_to_server.counter = 0
        client_to_server.sub_client_register.SetInParent()
        client_to_server.sub_client_register.udp_port = self.receive_port
        client_to_server.sub_client_register.client_index = self.client_index
        self.send(client_to_server)

        while not self.terminate:
            try:
                data, addr = self.udp_sock.recvfrom(65536)
                #print("Received data to sub client {1}: {0}".format(data, self.client_index))
                size = int.from_bytes(data[0:4], "big")
                if len(data) != size + 4:
                    print("Invalid subprocess data: {0}".format(data))
                    continue

                server_to_client = clientprotocol_pb2.ServerToClient()
                unpack_result = server_to_client.ParseFromString(data[4:])
                if unpack_result > 0:
                    if self.raw_receiver is not None:
                        self.raw_receiver(server_to_client)
                    if server_to_client.HasField("status_update"):
                        if self.status_information is not None:
                            self.status_information.update_status(server_to_client.status_update)
                        if self.receiver is not None:
                            self.receiver(self.status_information)
                        if server_to_client.HasField("status_update"):
                            if server_to_client.status_update.HasField("pos_update"):
                                if self.raw_pos_receiver is not None:
                                    self.raw_pos_receiver(server_to_client.status_update.pos_update)
                                if self.pos_receiver is not None:
                                    self.pos_receiver(self.status_information)
                            if self.raw_status_receiver is not None:
                                self.raw_status_receiver(server_to_client.status_update)
                            if self.status_receiver is not None:
                                self.status_receiver(self.status_information)
            except socket.timeout:
                continue

    def stop(self):
        self.terminate = True

    def send(self, client_to_server):
        protobuf_utils.protobuf_sendto(self.udp_sock, self.client_port, client_to_server)
