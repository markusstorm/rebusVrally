""" Logs in as different users from the same team and performs actions """
import argparse
import random
import socket
import sys
import tempfile
import threading
from time import sleep

import google
import requests

import rally.common.protobuf_utils as protobuf_utils
from client.client.server_connection import ServerConnection
from rally.common.rally_version import RallyVersion
from rally.common.rebuses import RebusStatus
from rally.protocol import serverprotocol_pb2, clientprotocol_pb2
from server.server_config import RebusConfig
from server.server_config_finder import ServerConfigFinder
from test.status_receiver import StatusReceiver


class OneUser(threading.Thread):
    def __init__(self, team, server_configuration, role_in_bus, teamname, username, password):
        threading.Thread.__init__(self)
        self.team = team
        self.role_in_bus = role_in_bus
        self.connection = None
        self.server_configuration = server_configuration
        self.teamname = teamname
        self.username = username
        self.password = password
        self.terminate = False
        self.user_id = None
        self.client_to_server_counter = 0
        self.status_receiver = None

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

            self.status_receiver = StatusReceiver(self.connection, self.on_position_update)
            self.status_receiver.start()

            # Select seat
            self.select_seat()
            # TODO: perform more actions

            self.perform_user_role()

            while not self.terminate:
                sleep(1)

    def perform_user_role(self):
        pass

    def on_position_update(self, status_information):
        pass

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


class Driver(OneUser):
    def __init__(self, team, server_configuration, i, teamname, username, password):
        self.status_information = None
        self.rand_speed = random.randrange(40, 50)
        OneUser.__init__(self, team, server_configuration, i, teamname, username, password)

    def perform_user_role(self):
        self.perform_driving()

    def perform_driving(self):
        while not self.terminate and self.status_information is None:
            sleep(1)

        wait_frame = 0
        wait_section = 0

        while not self.terminate:
            sleep(1)

            indicator = clientprotocol_pb2.ClientPositionUpdate.NONE
            track_information = self.server_configuration.track_information
            section_obj = track_information.get_section(self.status_information.current_section)
            if section_obj is not None:
                turn = section_obj.get_correct_turn()
                if turn is not None:
                    indicator = turn.direction

            if len(section_obj.rebus_places) > 0:
                current_frame = section_obj.calculate_default_video_frame_from_distance(self.status_information.distance)
                if self.status_information.current_section > wait_section or current_frame > wait_frame:
                    for rebus_place in section_obj.rebus_places:
                        if rebus_place.is_close_to(current_frame):
                            wait_frame = current_frame + 300
                            wait_section = self.status_information.current_section
                            team.search_for_rebus_checkpoint(rebus_place.number)
                            break

            if team.phase == Team.DRIVING:
                speed = self.rand_speed / 3.6
            else:
                speed = 0.0
            delta_distance = speed * 1.0
            client_to_server = clientprotocol_pb2.ClientToServer()
            client_to_server.pos_update.SetInParent()
            client_to_server.pos_update.speed = speed
            client_to_server.pos_update.delta_distance = delta_distance
            client_to_server.pos_update.current_section = 0 # TODO: is this used? Should it be removed?
            client_to_server.pos_update.indicator = indicator
            self.send_message_to_server(client_to_server)

    def on_position_update(self, status_information):
        self.status_information = status_information
        #print(status_information.distance)


class RebusSolver(OneUser):
    def __init__(self, team, server_configuration, i, teamname, username, password):
        self.status_information = None
        OneUser.__init__(self, team, server_configuration, i, teamname, username, password)

    def perform_user_role(self):
        while not self.terminate and self.status_information is None:
            sleep(1)

        self.perform_rebus_solving()

    def perform_rebus_solving(self):
        while not self.terminate:
            sleep(1)

            if self.team.phase == Team.LOOKING_FOR_REBUS:
                self.look_for_rebus()

            if self.team.phase == Team.SOLVING_REBUS:
                self.solve_rebus()

    def look_for_rebus(self):
        client_to_server = clientprotocol_pb2.ClientToServer()
        client_to_server.search_for_rebus.SetInParent()
        client_to_server.search_for_rebus.dummy = 0;
        self.send_message_to_server(client_to_server)

        #rc = self.server_configuration.get_rebus_config(self.team.which_rebus)
        while not self.terminate:
            sleep(1)
            txt, extra = self.status_information.rebus_statuses.get_rebus_number(self.team.which_rebus).get_text(RebusConfig.NORMAL)
            if txt is not None:
                print("Got rebus text: {0}".format(txt))
                self.team.solve_rebus(self.team.which_rebus)
                break

    def solve_rebus(self):
        rc = self.server_configuration.get_rebus_config(self.team.which_rebus)
        client_to_server = clientprotocol_pb2.ClientToServer()
        client_to_server.test_rebus_solution.SetInParent()
        client_to_server.test_rebus_solution.section = rc.section;
        client_to_server.test_rebus_solution.answer = rc.solution;
        client_to_server.test_rebus_solution.map_east = rc.east;
        client_to_server.test_rebus_solution.map_north = rc.north;
        self.send_message_to_server(client_to_server)

        while not self.terminate:
            sleep(1)

            if self.team.which_rebus in self.status_information.rebus_solutions:
                rs = self.status_information.rebus_solutions[self.team.which_rebus]
                #print(rs)
                if rs.target_east > 0 and rs.target_north > 0:
                    print("Solved the rebus!")
                    self.team.drive_to_next_rebus_checkpoint()
                    return

    def on_position_update(self, status_information):
        self.status_information = status_information
        print(status_information.distance, self.server_configuration.track_information.get_section(status_information.current_section).calculate_default_video_frame_from_distance(status_information.distance))


class Team:
    # Phases:
    INIT_PHASE = 0
    LOOKING_FOR_REBUS = 1
    SOLVING_REBUS = 2
    DRIVING = 3

    START_MORNING = 1
    START_BEFORE_RK1 = 2
    START_BEFORE_LUNCH = 3

    def __init__(self, server_configuration, number_of_users, teamname, password, team_number, start_phase):
        self.server_configuration = server_configuration
        self.number_of_users = number_of_users
        self.teamname = teamname
        self.password = password
        self.team_number = team_number
        self.users = {}
        self.phase = Team.INIT_PHASE
        self.start_phase = start_phase

        for i in range(1, number_of_users+1):
            username = "User{0}".format(i)
            self.users[username] = self.create_user(i, username)

    def search_for_rebus_checkpoint(self, rebus_number):
        print("Search for rebus")
        self.phase = Team.LOOKING_FOR_REBUS
        self.which_rebus = rebus_number

    def solve_rebus(self, rebus_number):
        print("Solve rebus")
        self.phase = Team.SOLVING_REBUS
        self.which_rebus = rebus_number

    def drive_to_next_rebus_checkpoint(self):
        print("Drive to next rebus checkpoint")
        self.phase = Team.DRIVING
        self.which_rebus = 0

    def run(self):
        if self.start_phase == Team.START_MORNING:
            warp_section = 1
            warp_frame = 0
        elif self.start_phase == Team.START_BEFORE_RK1:
            warp_section = 4
            warp_frame = 3030
        elif self.start_phase == Team.START_BEFORE_LUNCH:
            warp_section = 6
            warp_frame = 2330
        else:
            print("ERROR! Invalid start phase!")
            sys.exit(1)

        for user in self.users.values():
            print("Starting {0}".format(user.username))
            user.start()
            # Be nice and wait for some time until the next team member joins the server
            sleep(1)
        # TODO: define for how long the test shall continue

        # Prime the server
        url = "http://localhost:63352/warp/{0}/{1}".format(self.team_number, warp_section)
        #url = "http://localhost:63352/warp/{0}/4".format(self.team_number)
        data = str(warp_frame)
        #data = "800"
        x = requests.post(url, data=data)
        if x.status_code != 200:
            print("ERROR! Can't contact the server.")
        url = "http://localhost:63352/startrally".format(self.team_number)
        data = "0"
        x = requests.post(url, data=data)
        if x.status_code != 200:
            print("ERROR! Can't contact the server.")
        url = "http://localhost:63352/startafternoon".format(self.team_number)
        data = "0"
        x = requests.post(url, data=data)
        if x.status_code != 200:
            print("ERROR! Can't contact the server.")

        if self.start_phase == Team.START_MORNING:
            print("Starting at the morning rebus")
            self.phase = Team.SOLVING_REBUS
            self.which_rebus = 1 # Start with the morning rebus
        elif self.start_phase == Team.START_BEFORE_RK1:
            print("Starting before RK1")
            self.phase = Team.DRIVING
            self.which_rebus = 0
        elif self.start_phase == Team.START_BEFORE_LUNCH:
            print("Starting before lunch")
            self.phase = Team.DRIVING
            self.which_rebus = 0
        else:
            print("ERROR! Invalid start phase!")
            sys.exit(1)

        while True:
            sleep(1)
            print("Team phase: {0}".format(self.phase))

    def create_user(self, seat_index, username):
        if seat_index == 1: # Driver
            return Driver(self, self.server_configuration, seat_index, self.teamname, username, self.password)
        elif seat_index == 2: # Rebus solver
            return RebusSolver(self, self.server_configuration, seat_index, self.teamname, username, self.password)
        else:
            return OneUser(self, self.server_configuration, seat_index, self.teamname, username, self.password)


parser = argparse.ArgumentParser(description='Rebus test client. Simulates a team with some members')
parser.add_argument("-r", "--rally_configuration", type=str, help="Path to the rally configuration to use", required=True)
parser.add_argument("-t", "--team_id", type=int, help="The ID of the team to simulate", required=True)
parser.add_argument("-n", "--number_of_users", type=int, help="Number of users to simulate, default 1", required=False)
args = parser.parse_args()

config_finder = ServerConfigFinder(args.rally_configuration)
server_configuration = config_finder.rally_configs[0]

# print(server_configuration.track_information.get_section(4).calculate_default_video_distance_from_frame(3030))
# print(server_configuration.track_information.get_section(6).calculate_default_video_distance_from_frame(2330))
# sys.exit(1)
number_of_users = args.number_of_users
number_of_users = min(max(1, number_of_users), 9)

allowed_team = server_configuration.find_team_from_id(args.team_id)

team = Team(server_configuration, number_of_users, allowed_team.team_name, allowed_team.team_password, allowed_team.team_number, Team.START_MORNING)
team.run()
