import os.path
import xml.etree.ElementTree as ET

from rally.common.track_information import TrackInformation
from rally.protocol import serverprotocol_pb2


class ExtraPuzzle:
    def __init__(self, xml):
        self.id = ""
        self.title = ""
        self.cost = 0
        self.description = ""
        self.question = ""
        self.instructions = ""
        if "id" in xml.attrib:
            self.id = xml.attrib["id"]
        if "title" in xml.attrib:
            self.title = xml.attrib["title"]
        if "cost" in xml.attrib:
            self.cost = int(xml.attrib["cost"])
        for description in xml.findall("description"):
            self.description = description.text
        for question in xml.findall("question"):
            self.question = question.text
        for instructions in xml.findall("instructions"):
            self.instructions = instructions.text

    def build_client_config_xml(self, extra_puzzles_xml):
        puzzle_xml = ET.SubElement(extra_puzzles_xml, "extra_puzzle", id=self.id, title=self.title, cost=str(self.cost))
        if len(self.description) > 0:
            desc_xml = ET.SubElement(puzzle_xml, "description")
            desc_xml.text = self.description
        if len(self.question) > 0:
            question_xml = ET.SubElement(puzzle_xml, "question")
            question_xml.text = self.question
        # Dont' include the instructions


class BaseRallyConfig:
    def __init__(self, config_file):
        self.config_file = config_file
        self.location = os.path.dirname(config_file)
        self.rally_id = None
        self.has_difficulty = False
        self.track_information = None
        self.is_local = False
        self.title = None
        self.extra_puzzles = {}

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

    @staticmethod
    def xml_attribute_to_bool(value):
        return value.strip().casefold() == "true".casefold()

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
            self.has_difficulty = BaseRallyConfig.xml_attribute_to_bool(root.attrib["has_difficulty"])

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

        for extra_puzzles in root.findall("extra_puzzles"):
            for extra_puzzle in extra_puzzles.findall("extra_puzzle"):
                puzzle = ExtraPuzzle(extra_puzzle)
                self.extra_puzzles[puzzle.id] = puzzle

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
