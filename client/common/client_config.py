import os

from rally.common.rally_config import BaseRallyConfig
import xml.etree.ElementTree as ET


class ClientLoginConfig(BaseRallyConfig):
    def __init__(self, config_file):
        self.login_background = None
        self.seq_number = 0
        self.default_server_address = ""
        self.default_team_name = ""
        self.default_password = ""
        self.default_username = ""
        self.errors = []
        self.file_list_file = None
        BaseRallyConfig.__init__(self, config_file)

    def parse_xml(self, root):
        BaseRallyConfig.parse_xml(self, root)

        if "seq_number" in root.attrib:
            self.seq_number = float(root.attrib["seq_number"])

        if "login_background" in root.attrib:
            self.login_background = self.replace_locations(root.attrib["login_background"])

        if "file_list" in root.attrib:
            self.file_list_file = self.replace_locations(root.attrib["file_list"])
            self.validate_data_files()

        for login_details in root.findall("login_details"):
            if "server_address" in login_details.attrib:
                self.default_server_address = login_details.attrib["server_address"]
            if "team" in login_details.attrib:
                self.default_team_name = login_details.attrib["team"]
            if "password" in login_details.attrib:
                self.default_password = login_details.attrib["password"]
            if "username" in login_details.attrib:
                self.default_username = login_details.attrib["username"]

    def validate_data_files(self):
        self.errors = []
        if self.file_list_file is None:
            return True
        try:
            tree = ET.parse(self.file_list_file)
            root = tree.getroot()
            if root.tag != "files":
                self.errors.append("Felaktig valideringsfil: {0}".format(self.file_list_file))
                return False

            self.validate_dirs_and_files(root, os.path.abspath(os.path.dirname(self.file_list_file)))
            return len(self.errors) == 0
        except FileNotFoundError as e:
            self.errors.append("Valideringsfilen finns inte: {0}".format(self.file_list_file))
        except ET.ParseError as e:
            self.errors.append("Valideringsfilen är felaktig {0}: {1}".format(self.file_list_file, e.msg))
        return False

    def validate_dirs_and_files(self, xml_node, path):
        for dir_xml in xml_node.findall("dir"):
            if "name" in dir_xml.attrib:
                dir_name = dir_xml.attrib["name"]
                new_dir = os.path.abspath(os.path.join(path, dir_name))
                if os.path.exists(new_dir) and os.path.isdir(new_dir):
                    self.validate_dirs_and_files(dir_xml, new_dir)
                else:
                    self.errors.append("Missing directory {0}".format(new_dir))

        for file_xml in xml_node.findall("file"):
            if "name" in file_xml.attrib:
                file_name = file_xml.attrib["name"]
                file_path = os.path.abspath(os.path.join(path, file_name))
                if os.path.exists(file_path) and not os.path.isdir(file_path):
                    pass
                else:
                    self.errors.append("Missing file {0}".format(file_path))


class ClientRallyConfig(ClientLoginConfig):
    def __init__(self, config_file, data_path):
        self.data_path = data_path
        ClientLoginConfig.__init__(self, config_file)

    def parse_xml(self, root):
        BaseRallyConfig.parse_xml(self, root)

        if "seq_number" in root.attrib:
            self.seq_number = float(root.attrib["seq_number"])

        if "login_background" in root.attrib:
            self.login_background = self.replace_locations(root.attrib["login_background"])

        for login_details in root.findall("login_details"):
            if "server_address" in login_details.attrib:
                self.default_server_address = login_details.attrib["server_address"]
            if "team" in login_details.attrib:
                self.default_team_name = login_details.attrib["team"]
            if "password" in login_details.attrib:
                self.default_password = login_details.attrib["password"]
            if "username" in login_details.attrib:
                self.default_username = login_details.attrib["username"]

    def replace_locations(self, s):
        return BaseRallyConfig.replace_locations(self, s).replace("#DATA#", self.data_path)
