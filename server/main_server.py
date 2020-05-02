import datetime
import threading
import time

from rally.protocol import clientprotocol_pb2
from server.server_config import RebusConfig
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


class TimeScheduledAction(ScheduledAction):
    def __init__(self, schedule_time, action):
        ScheduledAction.__init__(self, 1, action)
        self.time = schedule_time

    def decrease_time(self):
        current_time = datetime.datetime.now().time()
        if current_time >= self.time:
            self.action()
            # Mark ourselves as done
            self.action = None


class ClientUpdateScheduler(threading.Thread):
    BACKUP_INTERVAL = 60

    def __init__(self, main_server):
        threading.Thread.__init__(self)
        self.main_server = main_server
        self.actions = []
        self.backup_counter = 0

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

            self.backup_counter += 1
            if self.backup_counter >= ClientUpdateScheduler.BACKUP_INTERVAL:
                self.backup_counter = 0
                for team_server in self.main_server.team_servers.values():
                    team_server.backup_status_to_disk()

    def schedule_action(self, seconds_from_now, action):
        self.actions.append(ScheduledAction(seconds_from_now, action))

    def schedule_action_obj(self, action_obj):
        self.actions.append(action_obj)


class BroadcastMessage:
    def __init__(self, message):
        self.message = message
        self.date_time = datetime.datetime.now()


class MainServer:
    def __init__(self, rally_configuration, backup_path):
        self.backup_path = backup_path
        self.team_servers = {}
        self.messages = []
        self.rally_is_started = False
        self.afternoon_is_started = False
        self.rally_configuration = rally_configuration
        self.track_information = self.rally_configuration.track_information

        self.scheduler = ClientUpdateScheduler(self)
        if rally_configuration.autostart_rally is not None:
            print("Scheduling autostart of rally at {0}".format(rally_configuration.autostart_rally))
            self.scheduler.schedule_action_obj(TimeScheduledAction(rally_configuration.autostart_rally, self.start_rally))
        if rally_configuration.autostart_lunch is not None:
            print("Scheduling autostart of afternoon at {0}".format(rally_configuration.autostart_lunch))
            self.scheduler.schedule_action_obj(TimeScheduledAction(rally_configuration.autostart_lunch, self.start_afternoon))

        self.scheduler.start()

        self.web_handler = WebHandler(self, self.rally_configuration.web_host, self.rally_configuration.web_port)
        self.web_handler.start()

    def find_team_server(self, team_name):
        if team_name in self.team_servers:
            return self.team_servers[team_name]
        return None

    def find_team_server_from_id(self, team_id):
        for team in self.team_servers.values():
            if team.team_number == team_id:
                return team
        return None

    def create_team_server(self, team_name, team_number, difficulty):
        ts = TeamServer(team_name, team_number, self.rally_configuration, self, difficulty, self.backup_path)
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
        rebus_config = self.rally_configuration.get_start_rebus_config()
        team_server.give_rebus_data(rebus_config.section, RebusConfig.NORMAL, rebus_config.normal, None)
        team_server.rally_is_started()
        #team_server.set_rally_stage(clientprotocol_pb2.ServerPositionUpdate.RallyStage.MORNING)

    def start_rally(self):
        print("{0}: Starting the rally".format(datetime.datetime.now().time()))
        self.rally_is_started = True
        self.add_message("Den första rebusen finns nu i ert rebusfönster hos protokollföraren. Lycka till!")
        for team_server in self.team_servers.values():
            self.start_rally_for_team_server(team_server)

    def start_afternoon_for_team_server(self, team_server):
        rebus_config = self.rally_configuration.get_lunch_rebus_config()
        team_server.give_rebus_data(rebus_config.section, RebusConfig.NORMAL, rebus_config.normal, None)
        # Can't really set the stage here... because then we could force a team to the afternoon if the are still working on the morning
        #team_server.set_rally_stage(clientprotocol_pb2.ServerPositionUpdate.RallyStage.AFTERNOON)

    def start_afternoon(self):
        print("{0}: Starting the afternoon".format(datetime.datetime.now().time()))
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

    def get_all_teams_json(self):
        json = {}
        for team_server in self.team_servers.values():
            json[team_server.team_number] = team_server.to_json()
        return json

    def get_team_json(self, team_number):
        for team_server in self.team_servers.values():
            if team_server.team_number == team_number:
                return team_server.to_json()
        return None

    def set_team_goal_time(self, team_number):
        for team_server in self.team_servers.values():
            if team_server.team_number == team_number:
                team_server.set_goal_time()

    def terminate_team(self, team_id):
        team_server = self.find_team_server_from_id(team_id)
        if team_server is not None:
            self.team_servers.pop(team_server.teamname, None)
            team_server.stop()

    def force_backup_team(self, team_id):
        team_server = self.find_team_server_from_id(team_id)
        if team_server is not None:
            team_server.backup_status_to_disk(True)
