from rally.common.config_finder import BaseConfigFinder
from server.server_config import ServerRallyConfig


class ServerConfigFinder(BaseConfigFinder):
    def __init__(self, specific_config=None):
        BaseConfigFinder.__init__(self,
                                  self.factory,
                                  ask_for_other_location=None,
                                  specific_config=specific_config)

    @staticmethod
    def factory(config_file):
        return ServerRallyConfig(config_file)
