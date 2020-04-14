import configparser
import os
import re

from rally.common.rally_config import RallyConfiguration


class ConfigFinder:
    """ Looks for rally configuration XML files and reads them """
    def __init__(self, is_server, ask_for_other_location, specific_config=None):
        self.rally_configs = []
        self.is_server = is_server
        # Guess that the config folder is located two folders down from the cwd
        if specific_config is not None and len(specific_config) > 0:
            self.read_config(specific_config)
            if len(self.rally_configs) == 0:
                print("ERROR! Unable to read rally configuration {0}!".format(specific_config))
        else:
            config_folder = os.path.abspath(os.path.join(os.getcwd(), "./config/"))
            if not os.path.exists(config_folder):
                config_folder = os.path.abspath(os.path.join(os.getcwd(), "../config/"))
            if not os.path.exists(config_folder):
                config_folder = os.path.abspath(os.path.join(os.getcwd(), "../../config/"))
            if os.path.exists(config_folder):
                self.read_config_folder(config_folder)
            if len(self.rally_configs) == 0:
                config_parser = configparser.ConfigParser()
                config_parser.read("startup.ini")
                if "config" in config_parser:
                    config_section = config_parser["config"]
                    if "config_path" in config_section and len(config_section["config_path"]) > 0:
                        path = config_section["config_path"]
                        path = os.path.abspath(path)
                        if os.path.isdir(path):
                            self.read_config_folder(path)
            if len(self.rally_configs) == 0:
                if ask_for_other_location is not None:
                    other_location = ask_for_other_location()
                    if other_location is not None and len(other_location) > 0:
                        if not os.path.isdir(other_location):
                            other_location = os.path.dirname(other_location)
                        self.read_config_folder(other_location)
                        if len(self.rally_configs) > 0:
                            config_parser = configparser.ConfigParser()
                            config_parser.read("startup.ini")
                            config_parser["config"] = {}
                            config_parser["config"]["config_path"] = other_location
                            with open("startup.ini", "w") as configout:
                                config_parser.write(configout)
            if len(self.rally_configs) == 0:
                print("ERROR! Unable to find any rally configurations in {0}!".format(config_folder))

    def read_config_folder(self, config_folder):
        files = [f for f in os.listdir(config_folder) if re.match(r'.*\.xml$', f)]
        for f in files:
            self.read_config(os.path.abspath(os.path.join(config_folder, f)))

    def read_config(self, file_to_read):
            try:
                config = RallyConfiguration(file_to_read, self.is_server)
                self.rally_configs.append(config)
            except ValueError as e:
                print(e)
                pass

    def get_rally_from_id(self, rally_id):
        for config in self.rally_configs:
            if config.rally_id.casefold() == rally_id.casefold():
                return config
        return None

    def get_rally_from_title(self, title):
        for config in self.rally_configs:
            if config.title == title:
                return config
        return None

    def get_newest_config(self):
        highest_seq = 0
        highest_config = None
        for config in self.rally_configs:
            if config.seq_number > highest_seq:
                highest_seq = config.seq_number
                highest_config = config
        return highest_config

    def get_all_titles(self):
        titles = []
        for config in self.rally_configs:
            titles.append(config.title)
        return titles

# sc = ConfigFinder(True, None)
# print(sc.rally_configs)
