import threading

from flask import Flask, request, jsonify


class WebHandler(threading.Thread):
    def __init__(self, main_server, host):
        threading.Thread.__init__(self)
        self.host = host
        self.main_server = main_server
        self.flask_app = Flask("rally_server")

        self.flask_app.add_url_rule("/", view_func=self.root)
        self.flask_app.add_url_rule("/index.html", view_func=self.root)

        self.flask_app.add_url_rule("/teams", view_func=self.get_teams)

        self.flask_app.add_url_rule("/teams/<id>", view_func=self.get_team_status)

        self.flask_app.add_url_rule("/sendmessage", view_func=self.send_message, methods=['POST'])
        self.flask_app.add_url_rule("/startrally", view_func=self.start_rally, methods=['POST'])
        self.flask_app.add_url_rule("/startafternoon", view_func=self.start_afternoon, methods=['POST'])

        self.flask_app.add_url_rule("/debug_restart", view_func=self.debug_restart, methods=['POST'])

    def run(self):
        self.flask_app.run(host=self.host, port=63352)

    def root(self):
        return self.flask_app.send_static_file('index.html')

    def get_teams(self):
        return "All teams and current login status"

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
