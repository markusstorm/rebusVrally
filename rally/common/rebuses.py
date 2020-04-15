from rally.protocol import clientprotocol_pb2
from server.server_config import RebusConfig


class RebusStatus:
    def __init__(self, section):
        self.section = section
        self.given_rebus_texts = {RebusConfig.NORMAL: None, RebusConfig.HELP: None, RebusConfig.SOLUTION: None}
        self.given_extra_texts = {RebusConfig.NORMAL: None, RebusConfig.HELP: None, RebusConfig.SOLUTION: None}

    def is_empty(self):
        return self.given_rebus_texts[RebusConfig.NORMAL] is None and \
               self.given_rebus_texts[RebusConfig.HELP] is None and \
               self.given_rebus_texts[RebusConfig.SOLUTION] is None and \
               self.given_extra_texts[RebusConfig.NORMAL] is None and \
               self.given_extra_texts[RebusConfig.HELP] is None and \
               self.given_extra_texts[RebusConfig.SOLUTION] is None

    def to_json(self):
        json = {"section": self.section,
                "given_rebuses": self.given_rebus_texts,
                "given_extra": self.given_extra_texts}
        return json

    def get_text(self, rebus_type):
        return self.given_rebus_texts[rebus_type], self.given_extra_texts[rebus_type]

    def give_rebus(self, rebus_type, txt, extra=None):
        self.given_rebus_texts[rebus_type] = txt
        self.given_extra_texts[rebus_type] = extra

    def fill_rebus_list(self, rebus_list):
        for rebus_type in self.given_rebus_texts:
            txt = self.given_rebus_texts[rebus_type]
            if txt is not None:
                rebus = clientprotocol_pb2.Rebus()
                rebus.section = self.section
                rebus.type = rebus_type
                rebus.rebus_text = txt
                extra = self.given_extra_texts[rebus_type]
                if extra is not None:
                    rebus.extra_text = extra
                rebus_list.rebuses.extend([rebus])

    def __str__(self):
        types = [RebusConfig.NORMAL, RebusConfig.HELP, RebusConfig.SOLUTION]
        to_str = {RebusConfig.NORMAL: "R", RebusConfig.HELP: "H", RebusConfig.SOLUTION: "S"}

        s = ""
        for rebus_type in types:
            txt = self.given_rebus_texts[rebus_type]
            if txt is not None:
                if len(s) > 0:
                    s += ", "
                else:
                    s = "["
                s += to_str[rebus_type] + str(self.section) + "=" + txt
        if len(s) > 0:
            s += "]"
        return s


class RebusStatuses:
    def __init__(self, rebus_configs):
        self.rebus_status = []
        if rebus_configs is not None:
            for rc in rebus_configs:
                self.rebus_status.append(RebusStatus(rc.section))

    def to_json(self):
        json = []
        for rs in self.rebus_status:
            if not rs.is_empty():
                json.append(rs.to_json())
        return json

    def find_rebus_section(self, section):
        for rs in self.rebus_status:
            if rs.section == section:
                return rs
        return None

    def give_rebus(self, section, rebus_type, txt, extra):
        rs = self.find_rebus_section(section)
        rs.give_rebus(rebus_type, txt, extra)

    def fill_rebus_list(self, rebus_list):
        for rs in self.rebus_status:
            rs.fill_rebus_list(rebus_list)

    def create_rebus(self, section):
        rs = RebusStatus(section)
        self.rebus_status.append(rs)
        return rs
