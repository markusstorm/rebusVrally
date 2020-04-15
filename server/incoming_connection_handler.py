import threading

from rally.common.rally_version import RallyVersion
from rally.protocol import serverprotocol_pb2
from server.serverside_client import ServerSideClient
import rally.common.protobuf_utils as protobuf_utils

import google.protobuf


class IncomingConnectionHandler(threading.Thread):
    def __init__(self, connection, addr, main_server):
        threading.Thread.__init__(self)
        self.connection = connection
        self.addr = addr
        self.main_server = main_server

    def run(self):
        with self.connection:
            # print('Connected by', addr)
            # while True:
            size = 0
            try:
                size_bytes = self.connection.recv(4)
                if not size_bytes:
                    return
                size = int.from_bytes(size_bytes[0:4], "big")
            except (ConnectionResetError, ConnectionAbortedError):
                print("Unidentified connection was closed")
                return
            # except:
            #     print("Unknown communications error ->")
            #     print("  Unidentified connection was closed")
            #     return

            try:
                data = self.connection.recv(size)
                if not data:
                    return
            except (ConnectionResetError, ConnectionAbortedError):
                print("Unidentified connection was closed")
                return
            # except:
            #     print("Unknown communications error ->")
            #     print("  Unidentified connection was closed")
            #     return
            # print(data)

            login_result = False
            error_message = "Unknown error"
            client = None
            try:
                loginrequest = serverprotocol_pb2.LoginRequest()

                unpack_result = loginrequest.ParseFromString(data)
                # unpack_result, data = protobuf_utils.protobuf_unpack(data, loginrequest)

                if unpack_result > 0:
                    if (not loginrequest.HasField("name") or
                            not loginrequest.HasField("teamname") or
                            not loginrequest.HasField("password") or
                            not loginrequest.HasField("version")):
                        login_result = False
                        error_message = "Missing data"
                    elif (len(loginrequest.teamname) == 0 or
                          len(loginrequest.name) == 0 or
                          len(loginrequest.password) == 0):
                        login_result = False
                        error_message = "A string is too short"
                    elif loginrequest.version != RallyVersion.VERSION:
                        login_result = False
                        error_message = "Incorrect version, the server is running version {0} and you {1}".format(RallyVersion.VERSION, loginrequest.version)
                    else:
                        team = self.main_server.rally_configuration.find_team(loginrequest.teamname)
                        if team is not None:
                            if team.team_password == loginrequest.password:
                                login_result = True
                                print("{0} connected to {1}".format(loginrequest.name, loginrequest.teamname))
                                difficulty = serverprotocol_pb2.LoginRequest.NORMAL
                                if self.main_server.rally_configuration.has_difficulty:
                                    if loginrequest.HasField("difficulty"):
                                        difficulty = loginrequest.difficulty
                                team_server = self.main_server.find_team_server(loginrequest.teamname)
                                if team_server is None:
                                    team_server = self.main_server.create_team_server(loginrequest.teamname, team.team_number, difficulty)
                                client = ServerSideClient(team_server, loginrequest.name, self.connection, self.main_server)
                            else:
                                error_message = "Incorrect password"
                        else:
                            error_message = "Unknown team"
            except google.protobuf.message.DecodeError as e:
                error_message = "Protocol error"

            loginresponse = serverprotocol_pb2.LoginResponse()
            loginresponse.success = login_result
            if client is not None:
                loginresponse.user_id = client.user_id
                loginresponse.configuration = self.main_server.rally_configuration.get_client_config_xml()
            loginresponse.message = error_message
            #try:
            protobuf_utils.protobuf_send(self.connection, loginresponse)
            if not loginresponse.success:
                print("Incorrect login attempt, closing connection")
                self.connection.close()
                return
            #except:
            #    pass
            if client is not None:
                client.run()
