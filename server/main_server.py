import datetime
import threading
import time

from rally.common.rally_config import RallyConfiguration, RebusConfig
from rally.protocol import clientprotocol_pb2
from server.team_server import TeamServer
from server.flask_server import WebHandler


class ScheduledAction:
    def __init__(self, seconds, action):
        self.seconds = seconds
        self.action = action

    def decrease_time(self):
        self.seconds -= 1
        if self.seconds <= 0:
            self.action()
            self.action = None

    def done(self):
        return self.action is None


class ClientUpdateScheduler(threading.Thread):
    def __init__(self, main_server):
        threading.Thread.__init__(self)
        self.main_server = main_server
        self.actions = []

    def run(self):
        while True:
            time.sleep(1)

            fired_actions = []
            for action in self.actions:
                action.decrease_time()
                if action.done():
                    fired_actions.append(action)

            for action in fired_actions:
                self.actions.remove(action)

            for team_server in self.main_server.team_servers.values():
                team_server.send_updates_to_clients()

    def schedule_action(self, seconds_from_now, action):
        self.actions.append(ScheduledAction(seconds_from_now, action))


class BroadcastMessage:
    def __init__(self, message):
        self.message = message
        self.date_time = datetime.datetime.now()


class MainServer:
    def __init__(self, rally_configuration, host):
        self.host = host
        self.team_servers = {}
        self.messages = []
        self.rally_is_started = False
        self.afternoon_is_started = False
        self.rally_configuration = rally_configuration
        self.track_information = self.rally_configuration.track_information

        self.scheduler = ClientUpdateScheduler(self)
        self.scheduler.start()

        self.web_handler = WebHandler(self, self.host)
        self.web_handler.start()

    def find_team_server(self, team_name):
        if team_name in self.team_servers:
            return self.team_servers[team_name]
        return None

    def create_team_server(self, team_name, team_number, difficulty):
        ts = TeamServer(team_name, team_number, self.rally_configuration, self, difficulty)
        self.team_servers[team_name] = ts
        if self.rally_is_started:
            self.start_rally_for_team_server(ts)
        if self.afternoon_is_started:
            self.start_afternoon_for_team_server(ts)
        return ts

    def add_message(self, s):
        message = BroadcastMessage(s)
        self.messages.append(message)
        self.send_broadcast_message(message)

    def start_rally_for_team_server(self, team_server):
        rebus_config = self.rally_configuration.get_start_rebus()
        team_server.give_rebus_data(rebus_config.section, RebusConfig.NORMAL, rebus_config.normal, None)

    def start_rally(self):
        self.rally_is_started = True
        self.add_message("Den första rebusen finns nu i ert rebusfönster hos protokollföraren. Lycka till!")
        for team_server in self.team_servers.values():
            self.start_rally_for_team_server(team_server)

    def start_afternoon_for_team_server(self, team_server):
        rebus_config = self.rally_configuration.get_lunch_rebus()
        team_server.give_rebus_data(rebus_config.section, RebusConfig.NORMAL, rebus_config.normal, None)

    def start_afternoon(self):
        self.afternoon_is_started = True
        self.add_message("Lunchrebusen finns nu i ert rebusfönster hos protokollföraren.")
        for team_server in self.team_servers.values():
            self.start_afternoon_for_team_server(team_server)

    def send_broadcast_message(self, message):
        server_to_client = clientprotocol_pb2.ServerToClient()
        server_to_client.broadcast_message.SetInParent()
        bc_message = server_to_client.broadcast_message
        bc_message.message = message.message
        bc_message.date_time = message.date_time.strftime("%Y-%m-%d, %H:%M:%S")

        for team_server in self.team_servers.values():
            team_server.send(server_to_client)

    def send_all_messages_to_client(self, client):
        for message in self.messages:
            server_to_client = clientprotocol_pb2.ServerToClient()
            server_to_client.broadcast_message.SetInParent()
            bc_message = server_to_client.broadcast_message
            bc_message.message = message.message
            bc_message.date_time = message.date_time.strftime("%Y-%m-%d, %H:%M:%S")
            client.send(server_to_client)

    def get_team_json(self, team_number):
        for team_server in self.team_servers.values():
            if team_server.team_number == team_number:
                return team_server.to_json()
        return None
