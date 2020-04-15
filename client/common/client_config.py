from rally.common.rally_config import BaseRallyConfig


class ClientLoginConfig(BaseRallyConfig):
    def __init__(self, config_file):
        self.login_background = None
        self.seq_number = 0
        self.default_server_address = ""
        self.default_team_name = ""
        self.default_password = ""
        self.default_username = ""
        BaseRallyConfig.__init__(self, config_file)

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
