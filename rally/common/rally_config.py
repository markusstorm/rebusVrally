import os.path
import xml.etree.ElementTree as ET

from rally.common.track_information import TrackInformation
from rally.protocol import serverprotocol_pb2


class BaseRallyConfig:
    def __init__(self, config_file):
        self.config_file = config_file
        self.location = os.path.dirname(config_file)
        self.rally_id = None
        self.has_difficulty = False
        self.track_information = None
        self.is_local = False
        self.title = None

        try:
            tree = ET.parse(config_file)
            root = tree.getroot()
            if root.tag != "rally":
                raise ValueError("{0} is not a rally configuration file!".format(config_file))

            self.parse_xml(root)
        except FileNotFoundError as e:
            raise ValueError("ERROR! Rally configuration file {0} not found! {1}".format(config_file, e))
        except ET.ParseError as e:
            raise ValueError("ERROR! Error when reading configuration {0}: {1}".format(config_file, e))

    def parse_xml(self, root):
        if "id" in root.attrib:
            self.rally_id = root.attrib["id"].strip()
        if self.rally_id is None or len(self.rally_id) == 0:
            raise ValueError("No rally 'id' specified in {0}".format(self.config_file))

        if "title" in root.attrib:
            self.title = root.attrib["title"].strip()
        if self.title is None or len(self.title) == 0:
            raise ValueError("No title specified in {0}".format(self.config_file))

        if "has_difficulty" in root.attrib:
            self.has_difficulty = root.attrib["has_difficulty"].strip().casefold() == "true".casefold()

        if "local" in root.attrib:
            self.is_local = root.attrib["local"].strip().casefold() == "true".casefold()

        print("Config: reading sections")
        for sections in root.findall("sections"):
            if self.track_information is None:
                if "file" in sections.attrib:
                    sections_file = self.replace_locations(sections.attrib["file"])
                    self.track_information = TrackInformation(self, config_file=sections_file)
                else:
                    self.track_information = TrackInformation(self, xml=sections)
            else:
                raise Exception("Can't define more than one <sections> in rally.xml")

    def replace_locations(self, s):
        return s.replace("#LOCATION#", self.location)

    def get_difficulties(self):
        if self.has_difficulty:
            return ["Normal", "Easy"]
        else:
            return ["Normal"]

    @staticmethod
    def get_difficulty_from_string(s):
        mapping = {"Normal": serverprotocol_pb2.LoginRequest.NORMAL, "Easy": serverprotocol_pb2.LoginRequest.EASY}
        if s is not None and len(s) > 0:
            if s in mapping:
                return mapping[s]
        return None
