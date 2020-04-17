import socket
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
        self.connection.settimeout(1)
        self.terminate = False

    def stop(self):
        #TODO: call
        print("IncomingConnectionHandler.stop()")
        self.terminate = True

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
                return False, None
        return False, None

    def run(self):
        with self.connection:
            success, size_bytes = self._receive_data(4)
            if not success:
                print("Unidentified connection from {0} was unsuccessful and will be closed".format(self.addr))
                return
            size = int.from_bytes(size_bytes[0:4], "big")

            success, data = self._receive_data(size)
            if not success:
                print("Unidentified connection from {0} didn't send expected data and will be closed".format(self.addr))
                return

            login_result = False
            error_message = "Unknown error"
            client = None
            try:
                loginrequest = serverprotocol_pb2.LoginRequest()

                unpack_result = loginrequest.ParseFromString(data)

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
                # Allow this error to be sent back to the client
            except Exception as e:
                print("Unknown error when accepting a connection: {0}".format(e))
                return

            try:
                loginresponse = serverprotocol_pb2.LoginResponse()
                loginresponse.success = login_result
                if client is not None:
                    loginresponse.user_id = client.user_id
                    loginresponse.configuration = self.main_server.rally_configuration.get_client_config_xml()
                loginresponse.message = error_message

                send_success = protobuf_utils.protobuf_send(self.connection, loginresponse)
                if not send_success:
                    print("Unable to send login response to client, closing connection")
                    return
            except Exception as e:
                print("Unknown exception when sending login response to client, closing connection. {0}".format(e))
                return

            if not loginresponse.success:
                print("Incorrect login attempt, closing connection")
                return

            if client is not None:
                client.run()
