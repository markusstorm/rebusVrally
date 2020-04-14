# Receive data from sub clients and send to the server, possibly listening in on the communication
import socket
import threading

from rally.protocol import clientprotocol_pb2


class SubProcessCommunicator(threading.Thread):
    UDP_IP = "127.0.0.1"

    def __init__(self, server_connection):
        threading.Thread.__init__(self)
        self.udp_sock = socket.socket(socket.AF_INET,  # Internet
                                      socket.SOCK_DGRAM)  # UDP
        self.udp_sock.settimeout(1)
        self.udp_sock.bind((SubProcessCommunicator.UDP_IP, 0))
        self.udp_port = self.udp_sock.getsockname()[1]
        print("Opened UDP port {0} for clients to communicate with".format(self.udp_port))

        self.clients = []
        self.terminate = False
        self.server_connection = server_connection

    def clear_clients(self):
        # TODO mutex?
        self.clients = []

    def stop(self):
        self.terminate = True

    def run(self):
        while not self.terminate:
            try:
                data, addr = self.udp_sock.recvfrom(65536)
                # print("Received data to proxy: {0}".format(data))
                size = int.from_bytes(data[0:4], "big")
                if len(data) != size + 4:
                    print("Invalid subprocess data: {0}".format(data))
                    continue
                # Send message on to the server
                # TODO: not really needed that we unpack the message and then pack it again...
                client_to_server = clientprotocol_pb2.ClientToServer()
                unpack_result = client_to_server.ParseFromString(data[4:])
                if unpack_result > 0:
                    if client_to_server.HasField("sub_client_register"):
                        # TODO: mutex?
                        print("Subclient {0} registered".format(client_to_server.sub_client_register.udp_port))
                        self.clients.append(client_to_server.sub_client_register.udp_port)
                    else:
                        self.server_connection.send_message_to_server(client_to_server)
            except socket.timeout:
                continue

    def send_to_sub_clients(self, server_to_client):
        packed = server_to_client.SerializeToString()
        size = len(packed)
        data = size.to_bytes(4, "big") + packed
        clients = self.clients.copy()
        for subclient_port in clients:
            # print("Send to client at {0}".format(subclient_port))
            self.udp_sock.sendto(data, ("127.0.0.1", subclient_port))
