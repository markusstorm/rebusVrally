from client.common.client_config import ClientLoginConfig
from rally.common.config_finder import BaseConfigFinder


class ClientConfigFinder(BaseConfigFinder):
    def __init__(self, ask_for_other_location, specific_config=None):
        BaseConfigFinder.__init__(self,
                                  self.factory,
                                  ask_for_other_location=ask_for_other_location,
                                  specific_config=specific_config)

    @staticmethod
    def factory(config_file):
        return ClientLoginConfig(config_file)
