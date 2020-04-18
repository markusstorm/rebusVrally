import threading

from flask import Flask, request, jsonify

import logging

class WebHandler(threading.Thread):
    def __init__(self, main_server, host):
        threading.Thread.__init__(self)
        self.host = host
        self.main_server = main_server

        # Turn off INFO logging from Flask
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        self.flask_app = Flask("rally_server")

        self.flask_app.add_url_rule("/", view_func=self.root)
        self.flask_app.add_url_rule("/index.html", view_func=self.root)
        self.flask_app.add_url_rule("/static/<file>", view_func=self.static_file)

        self.flask_app.add_url_rule("/teams", view_func=self.get_teams)

        self.flask_app.add_url_rule("/teams/<id>", view_func=self.get_team_status)

        self.flask_app.add_url_rule("/sendmessage", view_func=self.send_message, methods=['POST'])
        self.flask_app.add_url_rule("/startrally", view_func=self.start_rally, methods=['POST'])
        self.flask_app.add_url_rule("/startafternoon", view_func=self.start_afternoon, methods=['POST'])
        self.flask_app.add_url_rule("/endrally/<team_id>", view_func=self.end_rally_for_team, methods=['POST'])

        self.flask_app.add_url_rule("/debug_restart", view_func=self.debug_restart, methods=['POST'])

        self.flask_app.add_url_rule("/warp/<team_id>/<section>", view_func=self.warp_team, methods=['POST'])
        self.flask_app.add_url_rule("/terminate/<team_id>", view_func=self.terminate_team, methods=['POST'])
        self.flask_app.add_url_rule("/force_backup/<team_id>", view_func=self.force_backup_team, methods=['POST'])
        self.flask_app.add_url_rule("/debug_solved_start_rebus/<team_id>", view_func=self.debug_solved_start_rebus, methods=['POST'])
        self.flask_app.add_url_rule("/debug_solved_lunch_rebus/<team_id>", view_func=self.debug_solved_lunch_rebus, methods=['POST'])

    def run(self):
        self.flask_app.run(host=self.host, port=63352)

    def root(self):
        return self.flask_app.send_static_file('index.html')

    def static_file(self, file):
        return self.flask_app.send_static_file(file)

    def get_teams(self):
        return jsonify(self.main_server.get_all_teams_json())

    def get_team_status(self, id):
        int_id = 0
        try:
            int_id = int(id)
        except ValueError:
            return jsonify({"error": "Invalid team id, must be integer"})
        return jsonify(self.main_server.get_team_json(int_id))

    def send_message(self):
        if len(request.data) > 0:
            s = request.data.decode("utf-8")
            self.main_server.add_message(s)
        return ""

    def start_rally(self):
        self.main_server.start_rally()
        return ""

    def start_afternoon(self):
        self.main_server.start_afternoon()
        return ""

    def debug_restart(self):
        return "NOT implemented"

    def warp_team(self, team_id, section):
        team_server = self.main_server.find_team_server_from_id(int(team_id))
        frame = 0
        if len(request.data) > 0:
            s = request.data.decode("utf-8")
            frame = int(s)

        if team_server is not None:
            team_server.minibus.warp(int(section), int(frame))
        return ""

    def end_rally_for_team(self, team_id):
        team_server = self.main_server.find_team_server_from_id(int(team_id))
        if team_server is not None:
            team_server.end_rally()
        return ""

    def terminate_team(self, team_id):
        self.main_server.terminate_team(int(team_id))
        return ""

    def force_backup_team(self, team_id):
        self.main_server.force_backup_team(int(team_id))
        return ""

    def debug_solved_start_rebus(self, team_id):
        team_server = self.main_server.find_team_server_from_id(int(team_id))
        if team_server is not None:
            team_server.handle_solved_morning_rebus()
        return ""

    def debug_solved_lunch_rebus(self, team_id):
        team_server = self.main_server.find_team_server_from_id(int(team_id))
        if team_server is not None:
            team_server.handle_solved_lunch_rebus()
        return ""
