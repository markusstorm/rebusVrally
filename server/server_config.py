import xml.etree.ElementTree as ET

from rally.common.rally_config import BaseRallyConfig
from rally.common.track_information import TrackInformation


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
        if "name" in team_xml.attrib:
            self.team_name = team_xml.attrib["name"]
        if "number" in team_xml.attrib:
            self.team_number = int(team_xml.attrib["number"])
        if "password" in team_xml.attrib:
            self.team_password = team_xml.attrib["password"]

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
        self.rebuses = []
        self.allowed_teams = []
        self.start_messages = []
        BaseRallyConfig.__init__(self, config_file)

    def parse_xml(self, root):
        BaseRallyConfig.parse_xml(self, root)

        print("Config: reading start_messages")
        for start_messages in root.findall("start_messages"):
            for message in start_messages.findall("message"):
                # print("Start message: {0}".format(message.text))
                self.start_messages.append(message.text)

        print("Config: reading rebuses")
        for rebuses in root.findall("rebuses"):
            if "file" in rebuses.attrib:
                rebuses_file = self.replace_locations(rebuses.attrib["file"])
                self.rebuses = RebusConfig.read_file(rebuses_file)

        print("Config: reading teams")
        for teams in root.findall("teams"):
            if "file" in teams.attrib:
                teams_file = self.replace_locations(teams.attrib["file"])
                self.allowed_teams = AllowedTeam.read_file(teams_file)

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

    def get_client_config_xml(self):
        root = ET.Element("rally", id=self.rally_id, title=self.title)
        self.track_information.build_client_config_xml(root)

        tree = ET.ElementTree(root)
        xmlstr = ET.tostring(tree.getroot(), method='xml')
        print(xmlstr)
        return xmlstr


if __name__ == '__main__':
    #sr = ServerRallyConfig("../../server/configs/local_demo_rally.xml")
    sr = ServerRallyConfig("c:/Users/Markus/AppData/Local/Temp/tmp3bqtemp3")
    print(sr)
    print(sr.title)

