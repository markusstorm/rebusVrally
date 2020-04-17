import datetime
import socket

import google

from rally.protocol import clientprotocol_pb2
import rally.common.protobuf_utils as protobuf_utils


class ServerSideClient:
    """ Handles the connection with ONE client and all the communication """

    user_id_counter = 0

    def __init__(self, team_server, username, connection, main_server):
        # threading.Thread.__init__(self)
        self.main_server = main_server
        ServerSideClient.user_id_counter += 1
        self.user_id = ServerSideClient.user_id_counter
        self.team_server = team_server
        self.username = username
        self.connection = connection
        team_server.addClient(self)
        self.counter = 1
        self.terminate = False

    def stop(self):
        self.terminate = True

    def send(self, server_to_client):
        server_to_client.counter = self.counter
        self.counter += 1
        #try:
        # self.connection.sendall(server_to_client.SerializeToString())
        protobuf_utils.protobuf_send(self.connection, server_to_client)
        # except:
        #     pass

    def _remove_client(self):
        self.team_server.remove_client(self.user_id)

    def _receive_data(self, size):
        while not self.terminate:
            try:
                data = bytearray()
                while len(data) < size:
                    tmp = self.connection.recv(size-len(data))
                    if not tmp:
                        print("No data received for {0} in team {1} -> lost the connection".format(self.username, self.team_server.teamname))
                        # Lost the connection
                        return False, None
                    data.extend(tmp)
                return True, bytes(data)
            except socket.timeout:
                continue
            except (ConnectionResetError, ConnectionAbortedError):
                print("{0} in team {1} lost the connection".format(self.username, self.team_server.teamname))
                return False, None
            except Exception as e:
                print("ERROR! Unknown exception when receiving data: {0}".format(e))
                return False, e
        return False, None

    def run(self):
        self.main_server.send_all_messages_to_client(self)

        server_to_client = clientprotocol_pb2.ServerToClient()
        for txt in self.main_server.rally_configuration.start_messages:
            server_to_client.broadcast_message.SetInParent()
            welcome_message = server_to_client.broadcast_message
            welcome_message.message = txt
            welcome_message.date_time = datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
            self.send(server_to_client)

        while not self.terminate:
            success, size_bytes = self._receive_data(4)
            if not success:
                break
            size = int.from_bytes(size_bytes[0:4], "big")

            if size <= 0:
                print("Error in communications, size: {0}".format(size))
                break

            success, data = self._receive_data(size)
            if not success:
                print("{0} disconnected from {1}".format(self.username, self.team_server.teamname))
                break

            try:
                client_to_server = clientprotocol_pb2.ClientToServer()
                unpack_result = client_to_server.ParseFromString(data)
                if unpack_result > 0:
                    if client_to_server.HasField("select_seat"):
                        self.team_server.select_seat(client_to_server.select_seat)
                    if client_to_server.HasField("pos_update"):
                        self.team_server.update_pos_from_driver(client_to_server.pos_update)
                    if client_to_server.HasField("open_rebus_solution"):
                        self.team_server.open_rebus_solution(client_to_server.open_rebus_solution)
                    if client_to_server.HasField("set_photo_answer"):
                        self.team_server.set_photo_answer(client_to_server.set_photo_answer)
                    if client_to_server.HasField("set_plate_answer"):
                        self.team_server.set_plate_answer(client_to_server.set_plate_answer)
                    if client_to_server.HasField("set_rebus_answer"):
                        self.team_server.set_rebus_answer(client_to_server.set_rebus_answer)
                    if client_to_server.HasField("search_for_rebus"):
                        self.team_server.search_for_rebus()
                    if client_to_server.HasField("test_rebus_solution"):
                        self.team_server.test_rebus_solution(client_to_server.test_rebus_solution)
            except google.protobuf.message.DecodeError as e:
                print("Incorrect message from {0} disconnected from {1}: {2}".format(self.username, self.team_server.teamname, e))
                break
            except Exception as e:
                print("Unknown error in communication from {0} disconnected from {1}: {2}".format(self.username, self.team_server.teamname, e))
                break

        self.terminate = True # We exited the loop, so might as well set terminate to true
        self._remove_client()
        self.connection = None
        self.main_server = None

