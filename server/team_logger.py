import logging
import os


class TeamLoggerBase:
    def __init__(self, logger_id, log_path, filename):
        self.logger_id = logger_id
        self.log_path = log_path
        self.formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

        self.handler = logging.FileHandler(os.path.join(log_path, filename))
        self.handler.setFormatter(self.formatter)

        self.logger = logging.getLogger(logger_id)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.handler)

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def warning(self, message):
        self.logger.warning(message)


class TeamLogger(TeamLoggerBase):
    def __init__(self, team_id, log_path):
        self.team_id = team_id
        logger_id = "{0}.log"
        TeamLoggerBase.__init__(self, logger_id, log_path, "team_log.txt")


class TeamActionLogger(TeamLoggerBase):
    def __init__(self, team_id, log_path):
        logger_id = "{0}.actions"
        TeamLoggerBase.__init__(self, logger_id, log_path, "team_actions.txt")

    def log_penalty(self, number_of_points, message):
        self.warning("PENALTY ({0}): {1}".format(message, number_of_points))
