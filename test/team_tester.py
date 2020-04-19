""" Logs in as different users from the same team and performs actions """
import argparse
import socket
import tempfile
import threading
from time import sleep

import google

import rally.common.protobuf_utils as protobuf_utils
from client.client.server_connection import ServerConnection
from rally.common.rally_version import RallyVersion
from rally.protocol import serverprotocol_pb2, clientprotocol_pb2
from server.server_config_finder import ServerConfigFinder


class OneUser(threading.Thread):
    def __init__(self, server_configuration, role_in_bus, teamname, username, password):
        threading.Thread.__init__(self)
        self.role_in_bus = role_in_bus
        self.connection = None
        self.server_configuration = server_configuration
        self.teamname = teamname
        self.username = username
        self.password = password
        self.terminate = False
        self.user_id = None
        self.client_to_server_counter = 0

    def stop(self):
        self.terminate = True

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.connection = s

            # Login
            success, phase, message = self.login()
            if not success:
                print("Unable to log in {0} to the server: {1}".format(self.username, message))
                return False, 1

            # Select seat
            self.select_seat()
            # TODO: perform more actions



            while True:
                sleep(1)

    def select_seat(self):
        client_to_server = clientprotocol_pb2.ClientToServer()
        client_to_server.select_seat.SetInParent()
        client_to_server.select_seat.user_id = self.user_id
        client_to_server.select_seat.seat_index = self.role_in_bus
        self.send_message_to_server(client_to_server)

    def login(self):
        try:
            self.connection.connect(("127.0.0.1", ServerConnection.SERVER_PORT))
        except ConnectionRefusedError as e:
            return False, 0, "Connection error {0}".format(e)
        except socket.gaierror as e:
            return False, 0, "Invalid server address"
        # except Exception as e:
        #     return False, 0, "Unknown communications error: {0}".format(e)

        loginrequest = serverprotocol_pb2.LoginRequest()
        loginrequest.teamname = self.teamname
        loginrequest.name = self.username
        loginrequest.password = self.password
        loginrequest.version = RallyVersion.VERSION
        protobuf_utils.protobuf_send(self.connection, loginrequest)

        self.connection.settimeout(1)

        while not self.terminate:
            success, size_bytes = self._receive_data(4)
            if not success:
                return False, 1, "Unknown communications error: {0}".format(size_bytes)
            size = int.from_bytes(size_bytes[0:4], "big")

            success, data = self._receive_data(size)
            if not success:
                return False, 1, "Unknown communications error: {0}".format(data)

            try:
                loginresponse = serverprotocol_pb2.LoginResponse()
                unpack_result = loginresponse.ParseFromString(data)
                if unpack_result > 0:
                    if loginresponse.HasField("success"):
                        if loginresponse.success and loginresponse.HasField("user_id") and loginresponse.HasField("configuration"):
                            self.user_id = loginresponse.user_id
                            print("{0} logged in to server as user {1}".format(self.username, self.user_id))
                            temporary_config_file_fd, self.temporary_config_file = tempfile.mkstemp()
                            with open(temporary_config_file_fd, "wb") as f:
                                f.write(loginresponse.configuration.encode("utf-8"))
                            message = ""
                        else:
                            return False, 2, loginresponse.message
                return True, 2, None
            except google.protobuf.message.DecodeError as e:
                return False, 3, "Incorrect message from {0} disconnected from {1}: {2}".format(self.username, self.team_server.teamname, e)
            except Exception as e:
                return False, 4, "Unknown error in communication from {0} disconnected from {1}: {2}".format(self.username,self.team_server.teamname, e)
        return False, 5, "Terminated"

    def send_message_to_server(self, client_to_server):
        client_to_server.counter = self.client_to_server_counter
        self.client_to_server_counter += 1
        protobuf_utils.protobuf_send(self.connection, client_to_server)

    def _receive_data(self, size):
        while not self.terminate:
            try:
                data = bytearray()
                while len(data) < size:
                    tmp = self.connection.recv(size - len(data))
                    if not tmp:
                        print("No data received for {0} in team {1} -> lost the connection".format(self.username,
                                                                                                   self.team_name))
                        # Lost the connection
                        return False, None
                    data.extend(tmp)
                return True, bytes(data)
            except socket.timeout:
                continue
            except (ConnectionResetError, ConnectionAbortedError):
                print("{0} in team {1} lost the connection".format(self.username, self.team_name))
                return False, None
            # except Exception as e:
            #     print("ERROR! Unknown exception when receiving data: {0}".format(e))
            #     return False, e
        return False, None


class Team:
    def __init__(self, server_configuration, number_of_users, teamname, password):
        self.server_configuration = server_configuration
        self.number_of_users = number_of_users
        self.teamname = teamname
        self.users = {}
        for i in range(1, number_of_users+1):
            username = "User{0}".format(i)
            self.users[username] = OneUser(server_configuration, i, teamname, username, password)

    def run(self):
        for user in self.users.values():
            print("Starting {0}".format(user.username))
            user.start()
            # Be nice and wait for some time until the next team member joins the server
            sleep(1)
        # TODO: define for how long the test shall continue
        while True:
            sleep(1)


parser = argparse.ArgumentParser(description='Rebus test client. Simulates a team with some members')
parser.add_argument("-r", "--rally_configuration", type=str, help="Path to the rally configuration to use", required=True)
parser.add_argument("-t", "--team_id", type=int, help="The ID of the team to simulate", required=True)
parser.add_argument("-n", "--number_of_users", type=int, help="Number of users to simulate, default 1", required=False)
args = parser.parse_args()

config_finder = ServerConfigFinder(args.rally_configuration)
server_configuration = config_finder.rally_configs[0]

number_of_users = args.number_of_users
number_of_users = min(max(1, number_of_users), 9)

allowed_team = server_configuration.find_team_from_id(args.team_id)

team = Team(server_configuration, number_of_users, allowed_team.team_name, allowed_team.team_password)
team.run()
