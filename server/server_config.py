import datetime
import time
import xml.etree.ElementTree as ET

from rally.common.rally_config import BaseRallyConfig


class RebusConfig:
    NORMAL = 0
    HELP = 1
    SOLUTION = 2

    enum_to_string_map = {NORMAL: "Normal", HELP: "Help", SOLUTION: "Solution"}
    string_to_enum_map = {"Normal": NORMAL, "Help": HELP, "Solution": SOLUTION}

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
        for hlp in rebus_xml.findall("help"):
            if "text" in hlp.attrib:
                self.help = hlp.attrib["text"]
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
        self.is_start = False
        if "is_start" in rebus_xml.attrib:
            self.is_start = BaseRallyConfig.xml_attribute_to_bool(rebus_xml.attrib["is_start"])
        self.is_lunch = False
        if "is_lunch" in rebus_xml.attrib:
            self.is_lunch = BaseRallyConfig.xml_attribute_to_bool(rebus_xml.attrib["is_lunch"])
        self.found_lunch = False
        if "found_lunch" in rebus_xml.attrib:
            self.found_lunch = BaseRallyConfig.xml_attribute_to_bool(rebus_xml.attrib["found_lunch"])
        self.is_goal = False
        if "is_goal" in rebus_xml.attrib:
            self.is_goal = BaseRallyConfig.xml_attribute_to_bool(rebus_xml.attrib["is_goal"])

    @staticmethod
    def read_file(rebuses_file):
        try:
            tree = ET.parse(rebuses_file)
            root = tree.getroot()
            if root.tag != "rebuses":
                raise ValueError("{0} is not a rebus configuration file!".format(rebuses_file))

            rebuses = []
            for rebus_xml in root.findall("rebus"):
                rebus = RebusConfig(rebus_xml)
                rebuses.append(rebus)
            return rebuses
        except FileNotFoundError as e:
            raise ValueError("ERROR! Rebus configuration file {0} not found! {1}".format(rebuses_file, e))
        except ET.ParseError as e:
            raise ValueError("ERROR! Error when reading rebus configuration {0}: {1}".format(rebuses_file, e))


class AllowedTeam:
    def __init__(self, team_xml):
        self.team_name = None
        self.team_number = None
        self.team_password = None
        self.team_actual_name = None
        if "name" in team_xml.attrib:
            self.team_actual_name = team_xml.attrib["name"]
        if "login_name" in team_xml.attrib:
            self.team_name = team_xml.attrib["login_name"]
        if "number" in team_xml.attrib:
            self.team_number = int(team_xml.attrib["number"])
        if "password" in team_xml.attrib:
            self.team_password = team_xml.attrib["password"]
        if self.team_actual_name is None:
            self.team_actual_name = self.team_name

    def compare_name(self, team_name):
        return self.team_name.casefold() == team_name.casefold()

    @staticmethod
    def read_file(teams_file):
        try:
            tree = ET.parse(teams_file)
            root = tree.getroot()
            if root.tag != "teams":
                raise ValueError("{0} is not a teams configuration file!".format(teams_file))

            teams = []
            for team_xml in root.findall("team"):
                team = AllowedTeam(team_xml)
                teams.append(team)
            return teams
        except FileNotFoundError as e:
            raise ValueError("ERROR! Teans configuration file {0} not found! {1}".format(teams_file, e))
        except ET.ParseError as e:
            raise ValueError("ERROR! Error when reading teams configuration {0}: {1}".format(teams_file, e))


class ServerRallyConfig(BaseRallyConfig):
    def __init__(self, config_file):
        self.rebus_configs = []
        self.allowed_teams = []
        self.start_messages = []
        self.lunch_messages = []
        self.at_end_messages = []
        self.end_messages = []
        self.server_host = None
        self.server_port = None
        self.web_host = None
        self.web_port = None
        self.autostart_rally = None
        self.autostart_lunch = None
        BaseRallyConfig.__init__(self, config_file)

    def parse_xml(self, root):
        BaseRallyConfig.parse_xml(self, root)

        if "host" in root.attrib:
            self.server_host = root.attrib["host"]
        if self.server_host is None:
            self.server_host = "127.0.0.1"
        if "port" in root.attrib:
            self.server_port = int(root.attrib["port"])
        if self.server_port is None:
            self.server_port = 63332
        if "web_host" in root.attrib:
            self.web_host = root.attrib["web_host"]
        if self.web_host is None:
            self.web_host = "127.0.0.1"
        if "web_port" in root.attrib:
            self.web_port = int(root.attrib["web_port"])
        if self.web_port is None:
            self.web_port = 61333
        if "autostart_rally" in root.attrib:
            self.autostart_rally = ServerRallyConfig.time_from_string(root.attrib["autostart_rally"])
        if "autostart_lunch" in root.attrib:
            self.autostart_lunch = ServerRallyConfig.time_from_string(root.attrib["autostart_lunch"])

        print("Config: reading start_messages")
        for start_messages in root.findall("start_messages"):
            for message in start_messages.findall("message"):
                self.start_messages.append(message.text)
        for lunch_messages in root.findall("lunch_messages"):
            for message in lunch_messages.findall("message"):
                self.lunch_messages.append(message.text)
        for at_end_messages in root.findall("at_end_messages"):
            for message in at_end_messages.findall("message"):
                self.at_end_messages.append(message.text)
        for end_messages in root.findall("end_messages"):
            for message in end_messages.findall("message"):
                self.end_messages.append(message.text)

        print("Config: reading rebuses")
        for rebuses in root.findall("rebuses"):
            if "file" in rebuses.attrib:
                rebuses_file = self.replace_locations(rebuses.attrib["file"])
                self.rebus_configs = RebusConfig.read_file(rebuses_file)

        print("Config: reading teams")
        for teams in root.findall("teams"):
            if "file" in teams.attrib:
                teams_file = self.replace_locations(teams.attrib["file"])
                self.allowed_teams = AllowedTeam.read_file(teams_file)

    @staticmethod
    def time_from_string(s):
        try:
            if s is not None and len(s) > 0:
                return datetime.datetime.strptime(s, "%H:%M").time()
                #time.strptime(s, "%H:%M")
        except ValueError as e:
            print("Unable to restore time '{0}' from string. Error: {1}".format(s, e))
        return None

    def has_team(self, team_name):
        team = self.find_team(team_name)
        return team is not None

    def find_team(self, team_name):
        for team in self.allowed_teams:
            if team.compare_name(team_name):
                return team
        return None

    def find_team_from_id(self, team_id):
        for team in self.allowed_teams:
            if team.team_number == team_id:
                return team
        return None

    def get_rebus_config(self, section):
        for rebus_config in self.rebus_configs:
            if rebus_config.section == section:
                return rebus_config
        return None

    def get_start_rebus_config(self):
        for rebus_config in self.rebus_configs:
            if rebus_config.is_start:
                return rebus_config
        return None

    def get_lunch_rebus_config(self):
        for rebus_config in self.rebus_configs:
            if rebus_config.is_lunch:
                return rebus_config
        return None

    def get_goal_rebus_config(self):
        for rebus_config in self.rebus_configs:
            if rebus_config.is_goal:
                return rebus_config
        return None

    def get_client_config_xml(self):
        root = ET.Element("rally", id=self.rally_id, title=self.title)
        self.track_information.build_client_config_xml(root)
        if len(self.extra_puzzles) > 0:
            extra_puzzles_xml = ET.SubElement(root, "extra_puzzles")
            for extra_puzzle in self.extra_puzzles.values():
                extra_puzzle.build_client_config_xml(extra_puzzles_xml)

        tree = ET.ElementTree(root)
        xmlstr = ET.tostring(tree.getroot(), method='xml')
        return xmlstr


# if __name__ == '__main__':
#     #sr = ServerRallyConfig("../../server/configs/local_demo_rally.xml")
#     sr = ServerRallyConfig("c:/Users/Markus/AppData/Local/Temp/tmp3bqtemp3")
#     print(sr)
#     print(sr.title)

