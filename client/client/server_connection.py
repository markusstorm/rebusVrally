import os
import socket
import tempfile
import threading
import time

import rally.common.protobuf_utils as protobuf_utils
from client.client.subprocess_communicator import SubProcessCommunicator
from rally.common.rally_version import RallyVersion
from rally.common.status_information import StatusInformation
from rally.protocol import serverprotocol_pb2, clientprotocol_pb2

#HOST = '127.0.0.1'  # The server's hostname or IP address
SERVER_PORT = 63332  # The port used by the server


class ServerConnection(threading.Thread):
    def __init__(self, server, team_name, password, username, report_login_result, report_lost_connection, difficulty):
        threading.Thread.__init__(self)
        self.connection = None
        self.server = server
        self.team_name = team_name
        self.password = password
        self.username = username
        self.report_login_result = report_login_result
        self.report_lost_connection = report_lost_connection
        self.difficulty = difficulty
        self.subprocess_communicator = None
        self.message_receiver = None
        self.terminate = False
        self.counter = 1
        self.status_information = StatusInformation()
        self.enter_client_loop = False
        self.logged_in = False
        self.temporary_config_file = None

    def stop(self):
        self.terminate = True
        self.subprocess_communicator.stop()

    def start_client_loop(self, on_lost_connection, on_message_received, subprocess_communicator):
        self.subprocess_communicator = subprocess_communicator
        self.report_lost_connection = on_lost_connection
        self.message_receiver = on_message_received
        self.enter_client_loop = True

    def send_message_to_server(self, client_to_server):
        client_to_server.counter = self.counter
        self.counter += 1
        protobuf_utils.protobuf_send(self.connection, client_to_server)

    def get_current_speed(self):
        if self.status_information is not None:
            return self.status_information.speed
        return 0

    def update_status_pos(self, pos_update):
        self.status_information.update_pos(pos_update)

    def update_status_seating(self, seating_update):
        self.status_information.update_seating(seating_update)

    def update_status(self, su_message):
        if su_message.HasField("pos_update"):
            self.update_status_pos(su_message.pos_update)
        if su_message.HasField("bus_seating"):
            self.update_status_seating(su_message.bus_seating)

    def login_phase(self):
        try:
            self.connection.connect((self.server, SERVER_PORT))
        except ConnectionRefusedError as e:
            print("Connection error {0}".format(e))
            # TODO: tell the user that we can't contact the server
            self.report_login_result(False, "Connection error {0}".format(e))
            return
        except socket.gaierror as e:
            print("Invalid server address")
            self.report_login_result(False, "Invalid server address")
            return
        except:
            print("Unknown communications error")
            self.report_login_result(False, "Unknown communications error")
            return
        loginrequest = serverprotocol_pb2.LoginRequest()
        loginrequest.teamname = self.team_name
        loginrequest.name = self.username
        loginrequest.password = self.password
        loginrequest.version = RallyVersion.VERSION
        if self.difficulty is not None:
            loginrequest.difficulty = self.difficulty
        protobuf_utils.protobuf_send(self.connection, loginrequest)
        self.logged_in = False
        message = "Unknown login error"
        self.connection.settimeout(1)
        # data = bytearray(65536)
        while not self.terminate:
            # view = memoryview(data)
            size = 0
            try:
                size_bytes = self.connection.recv(4)
                if not size_bytes:
                    break
                size = int.from_bytes(size_bytes[0:4], "big")
            except ConnectionResetError:
                if self.report_lost_connection:
                    self.report_lost_connection()
                print("Lost connection")
                break
            except socket.timeout:
                continue
            try:
                data = self.connection.recv(size)
                if not data:
                    break
                # print('Received', repr(data))
                loginresponse = serverprotocol_pb2.LoginResponse()
                unpack_result = loginresponse.ParseFromString(data)
                # unpack_result, data = protobuf_utils.protobuf_unpack(data, loginresponse)
                if unpack_result > 0:
                    if loginresponse.HasField("success"):
                        if loginresponse.success and loginresponse.HasField("user_id") and loginresponse.HasField("configuration"):
                            print("Logged in to server")
                            self.logged_in = True
                            self.status_information.user_id = loginresponse.user_id
                            self.status_information.username = self.username
                            temporary_config_file_fd, self.temporary_config_file = tempfile.mkstemp()
                            #print("Created temporary file {0} to store the configuration".format(self.temporary_config_file))
                            #print(loginresponse.configuration)
                            with open(temporary_config_file_fd, "wb") as f:
                                f.write(loginresponse.configuration.encode("utf-8"))
                            message = ""
                        else:
                            if loginresponse.HasField("message"):
                                message = loginresponse.message
                # TODO: show message to the user
                break
            except ConnectionResetError:
                print("Lost connection")
                break
            except socket.timeout:
                continue

        if self.terminate:
            return

        self.report_login_result(self.logged_in, message)

    def client_loop(self):
        while not self.terminate:
            try:
                size_bytes = self.connection.recv(4)
                if not size_bytes:
                    break
                size = int.from_bytes(size_bytes[0:4], "big")
            except ConnectionResetError:
                print("Lost connection")
                if self.report_lost_connection:
                    self.report_lost_connection()
                break
            except socket.timeout:
                continue
            except:
                print("Server communications error")
                if self.report_lost_connection:
                    self.report_lost_connection()
                break
            try:
                data = self.connection.recv(size)
                if not data:
                    break
                # print('Received', repr(data))
                while len(data) > 0:
                    server_to_client = clientprotocol_pb2.ServerToClient()
                    unpack_result = server_to_client.ParseFromString(data)
                    if unpack_result > 0:
                        data = data[unpack_result:]
                        # print(server_to_client)
                        if server_to_client.HasField("broadcast_message"):
                            bc_message = server_to_client.broadcast_message
                            if self.message_receiver is not None:
                                self.message_receiver(bc_message)
                        if server_to_client.HasField("status_update"):
                            su_message = server_to_client.status_update
                            self.update_status(su_message)
                            self.subprocess_communicator.send_to_sub_clients(server_to_client)

                    else:
                        # Possibly loosing something now
                        break
            except ConnectionResetError:
                print("Lost connection")
                self.report_lost_connection()
                break
            except socket.timeout:
                continue
            # except:
            #     print("Server communications error 2 ")
            #     lost_connection()
            #     break

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.connection = s

            self.login_phase()

            if not self.logged_in:
                return

            while not self.enter_client_loop:
                time.sleep(0.1)

            self.client_loop()
