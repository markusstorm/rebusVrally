import logging
import os


class TeamLoggerBase:
    def __init__(self, team_id, logger_id, log_path, filename):
        self.team_id = team_id
        self.logger_id = logger_id
        self.log_path = log_path
        self.formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

        self.handler = logging.FileHandler(os.path.join(log_path, filename))
        self.handler.setFormatter(self.formatter)

        self.logger = logging.getLogger(logger_id)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.handler)

    def info(self, message):
        self.add_to_server_log("INFO", message)
        self.logger.info(message)

    def error(self, message):
        self.add_to_server_log("ERROR", message)
        self.logger.error(message)

    def warning(self, message):
        self.add_to_server_log("WARNING", message)
        self.logger.warning(message)

    def add_to_server_log(self, level, message):
        print("{0}: {1} {2}".format(self.team_id, level, message))


class TeamLogger(TeamLoggerBase):
    def __init__(self, team_id, log_path):
        logger_id = "{0}.log".format(team_id)
        TeamLoggerBase.__init__(self, team_id, logger_id, log_path, "team_log.txt")


class TeamActionLogger(TeamLoggerBase):
    def __init__(self, team_id, log_path):
        logger_id = "{0}.actions".format(team_id)
        TeamLoggerBase.__init__(self, team_id, logger_id, log_path, "team_actions.txt")

    def log_penalty(self, number_of_points, message):
        self.info("PENALTY ({0}): {1}".format(message, number_of_points))

    def log_warning(self, message):
        self.warning(message)
