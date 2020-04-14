import xml.etree.ElementTree as ET
from rally.common.track_information import TrackInformation
import os.path
from rally.protocol import serverprotocol_pb2


class RebusConfig:
    NORMAL = 0
    HELP = 1
    SOLUTION = 2

    def __init__(self, rebus_xml):
        self.section = 0
        self.normal = None
        self.help = None
        self.solution = None
        self.east = 0
        self.north = 0
        self.target_description = None
        self.target_east = 0
        self.target_north = 0
        self.target_picture = None
        if "section" in rebus_xml.attrib:
            self.section = int(rebus_xml.attrib["section"])
        for normal in rebus_xml.findall("normal"):
            if "text" in normal.attrib:
                self.normal = normal.attrib["text"]
        for help in rebus_xml.findall("help"):
            if "text" in help.attrib:
                self.help = help.attrib["text"]
        for solution in rebus_xml.findall("solution"):
            if "text" in solution.attrib:
                self.solution = solution.attrib["text"]
        if "map_east" in rebus_xml.attrib:
            self.east = int(rebus_xml.attrib["map_east"])
        if "map_north" in rebus_xml.attrib:
            self.north = int(rebus_xml.attrib["map_north"])
        for target in rebus_xml.findall("target"):
            if "description" in target.attrib:
                self.target_description = target.attrib["description"]
            if "map_east" in target.attrib:
                self.target_east = int(target.attrib["map_east"])
            if "map_north" in target.attrib:
                self.target_north = int(target.attrib["map_north"])
            if "zoomed_map_url" in target.attrib:
                self.target_picture = target.attrib["zoomed_map_url"]


class AllowedTeam:
    def __init__(self, team_xml):
        self.team_name = None
        self.team_number = None
        self.team_password = None
        if "name" in team_xml.attrib:
            self.team_name = team_xml.attrib["name"]
        if "number" in team_xml.attrib:
            self.team_number = int(team_xml.attrib["number"])
        if "password" in team_xml.attrib:
            self.team_password = team_xml.attrib["password"]

    def compare_name(self, team_name):
        return self.team_name.casefold() == team_name.casefold()


class RallyConfiguration:

    def __init__(self, super_config_file, server):
        self.file_name = super_config_file
        self.location = os.path.dirname(super_config_file)
        self.title = None
        self.rally_id = None
        self.is_local = False
        self.has_difficulty = False
        self.seq_number = 0
        self.default_server_address = ""
        self.default_team_name = ""
        self.default_password = ""
        self.default_username = ""

        file_to_read = self.find_actual_file_to_read(super_config_file, server)
        # Adjust to start reading the actual configuration
        self.location = os.path.dirname(file_to_read)

        self.track_information = None
        self.rebuses = []
        self.allowed_teams = []
        self.login_background = None
        self.start_messages = []

        try:
            tree = ET.parse(file_to_read)
            root = tree.getroot()
            self.parse_xml(root)
        except FileNotFoundError as e:
            raise ValueError("ERROR! Rally configuration file {0} not found! {1}".format(file_to_read, e))
        except ET.ParseError as e:
            raise ValueError("ERROR! Error when reading configuration {0}: {1}".format(file_to_read, e))

    def parse_xml(self, root):
        if root.tag != "rally":
            raise ValueError("Not a rally configuration file!")

        if "login_background" in root.attrib:
            self.login_background = self.replace_location(root.attrib["login_background"])

        for login_details in root.findall("login_details"):
            if "server_address" in login_details.attrib:
                self.default_server_address = login_details.attrib["server_address"]
            if "team" in login_details.attrib:
                self.default_team_name = login_details.attrib["team"]
            if "password" in login_details.attrib:
                self.default_password = login_details.attrib["password"]
            if "username" in login_details.attrib:
                self.default_username = login_details.attrib["username"]

        for start_messages in root.findall("start_messages"):
            for message in start_messages.findall("message"):
                #print("Start message: {0}".format(message.text))
                self.start_messages.append(message.text)

        for sections in root.findall("sections"):
            if self.track_information is None:
                if "file" in sections.attrib:
                    sections_file = self.replace_location(sections.attrib["file"])
                    #sections_file = os.path.join(os.path.dirname(file_to_read), file)
                    self.track_information = TrackInformation(sections_file)
            else:
                raise Exception("Can't define more than one <sections> in rally.xml")

        for rebuses in root.findall("rebuses"):
            for rebus_xml in rebuses.findall("rebus"):
                rebus = RebusConfig(rebus_xml)
                self.rebuses.append(rebus)

        for teams in root.findall("teams"):
            for team_xml in teams.findall("team"):
                team = AllowedTeam(team_xml)
                #print(team)
                self.allowed_teams.append(team)

    def find_actual_file_to_read(self, super_config_file, server):
        tree = ET.parse(super_config_file)
        root = tree.getroot()

        if root.tag != "rally":
            raise ValueError("{0} is not a rally configuration file!".format(super_config_file))

        if "title" in root.attrib:
            self.title = root.attrib["title"].strip()
        if self.title is None or len(self.title) == 0:
            raise ValueError("No title specified in {0}".format(super_config_file))

        if "id" in root.attrib:
            self.rally_id = root.attrib["id"].strip()
        if self.rally_id is None or len(self.rally_id) == 0:
            raise ValueError("No rally 'id' specified in {0}".format(super_config_file))

        if "seq_number" in root.attrib:
            self.seq_number = float(root.attrib["seq_number"])

        if "local" in root.attrib:
            self.is_local = root.attrib["local"].strip().casefold() == "true".casefold()

        if "has_difficulty" in root.attrib:
            self.has_difficulty = root.attrib["has_difficulty"].strip().casefold() == "true".casefold()

        config_file = None
        if server:
            for server_config in root.findall("server_config"):
                if "file" in server_config.attrib:
                    file = server_config.attrib["file"]
                    config_file = os.path.abspath(self.replace_location(file))
        else:
            for client_config in root.findall("client_config"):
                if "file" in client_config.attrib:
                    file = client_config.attrib["file"]
                    config_file = os.path.abspath(self.replace_location(file))

        if config_file is None:
            if server:
                raise ValueError("Missing server_config in {0}".format(super_config_file))
            else:
                raise ValueError("Missing client_config in {0}".format(super_config_file))

        return config_file

    def replace_location(self, s):
        return s.replace("#LOCATION#", self.location)

    def has_team(self, team_name):
        team = self.find_team(team_name)
        return team is not None

    def find_team(self, team_name):
        for team in self.allowed_teams:
            if team.compare_name(team_name):
                return team
        return None

    def get_rebus(self, section):
        for rebus in self.rebuses:
            if rebus.section == section:
                return rebus
        return None

    def get_start_rebus(self):
        # TODO: configure?
        return self.get_rebus(1)

    def get_lunch_rebus(self):
        # TODO: configure?
        return self.get_rebus(5)

    def get_difficulties(self):
        if self.has_difficulty:
            return ["Normal", "Easy"]
        else:
            return ["Normal"]

    def get_difficulty_from_string(self, s):
        mapping = {"Normal": serverprotocol_pb2.LoginRequest.NORMAL, "Easy": serverprotocol_pb2.LoginRequest.EASY}
        if s is not None and len(s) > 0:
            if s in mapping:
                return mapping[s]
        return None


# r = RallyConfiguration("../../data/rally.xml")
# print(r)
