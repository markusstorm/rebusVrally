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
        json = {"rebus-number": self.section}
        given = {}
        for key in self.given_rebus_texts:
            if self.given_rebus_texts[key] is not None:
                given[RebusConfig.enum_to_string_map[key]] = self.given_rebus_texts[key]
        json["given_rebuses"] = given
        extra = {}
        for key in self.given_extra_texts:
            if self.given_extra_texts[key] is not None:
                extra[RebusConfig.enum_to_string_map[key]] = self.given_extra_texts[key]
        json["given_extra"] = extra
        return json

    @staticmethod
    def from_json(_json):
        if "rebus-number" in _json:
            section = _json["rebus-number"]
            rs = RebusStatus(section)
            if "given_rebuses" in _json:
                given_json = _json["given_rebuses"]
                for key in given_json:
                    rs.given_rebus_texts[RebusConfig.string_to_enum_map[key]] = given_json[key]
            if "given_extra" in _json:
                given_json = _json["given_extra"]
                for key in given_json:
                    rs.given_extra_texts[RebusConfig.string_to_enum_map[key]] = given_json[key]
            return rs
        return None

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
    def __init__(self):
        self.rebus_statuses = {}

    def to_json(self):
        json = []
        for rebus_number in self.rebus_statuses:
            rs = self.rebus_statuses[rebus_number]
            if not rs.is_empty():
                json.append(rs.to_json())
        return json

    def restore_from_json(self, _json):
        self.rebus_statuses = {}
        for rs_json in _json:
            rs = RebusStatus.from_json(rs_json)
            if rs is not None:
                self.rebus_statuses[rs.section] = rs

    def get_rebus_number(self, rebus_number):
        if rebus_number in self.rebus_statuses:
            return self.rebus_statuses[rebus_number]
        rs = RebusStatus(rebus_number)
        self.rebus_statuses[rebus_number] = rs
        return rs

    def give_rebus(self, rebus_number, rebus_type, txt, extra):
        rs = self.get_rebus_number(rebus_number)
        rs.give_rebus(rebus_type, txt, extra)

    def fill_rebus_list(self, rebus_list):
        for rs in self.rebus_statuses.values():
            rs.fill_rebus_list(rebus_list)
