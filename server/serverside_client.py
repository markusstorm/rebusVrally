import datetime

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

    def run(self):
        self.main_server.send_all_messages_to_client(self)

        server_to_client = clientprotocol_pb2.ServerToClient()
        for txt in self.main_server.rally_configuration.start_messages:
            server_to_client.broadcast_message.SetInParent()
            welcome_message = server_to_client.broadcast_message
            welcome_message.message = txt
            welcome_message.date_time = datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
            self.send(server_to_client)
        while True:
            size = -1
            try:
                size_bytes = self.connection.recv(4)
                if not size_bytes:
                    print("{0} disconnected from {1}".format(self.username, self.team_server.teamname))
                    break
                size = int.from_bytes(size_bytes[0:4], "big")
            except (ConnectionResetError, ConnectionAbortedError):
                print("{0} disconnected from {1}".format(self.username, self.team_server.teamname))
                # self._remove_client()
                break
            # except:
            #     print("Unknown communications error ->")
            #     print("  {0} disconnected from {1}".format(self.username, self.team_server.teamname))
            #     break
            if size <= 0:
                print("Error in communications, size: {0}".format(size))
                # self._remove_client()
                break

            try:
                data = self.connection.recv(size)
                if not data:
                    print("{0} disconnected from {1}".format(self.username, self.team_server.teamname))
                    break

                print(data)
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


            except (ConnectionResetError, ConnectionAbortedError):
                print("{0} disconnected from {1}".format(self.username, self.team_server.teamname))
                break
            # except:
            #     print("Unknown communications error ->")
            #     print("  {0} disconnected from {1}".format(self.username, self.team_server.teamname))
            #     break
        self._remove_client()
