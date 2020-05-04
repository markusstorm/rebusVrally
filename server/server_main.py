import argparse
import datetime
import os
import socket
import sys
import threading

from flask import Flask

from server.incoming_connection_handler import IncomingConnectionHandler
from server.main_server import MainServer



# def foo():
#     return "Hello World!"
# flask_app = Flask("tmp")
# flask_app.add_url_rule("/", view_func=foo)
# flask_app.run(host='0.0.0.0')
from server.server_config_finder import ServerConfigFinder

parser = argparse.ArgumentParser(description='Rebus server')
parser.add_argument("-r", "--rally_configuration", type=str, help="Path to the rally configuration to use", required=False)
parser.add_argument("-l", "--start_locally", action='store_true', help="Start the server on 127.0.0.1", required=False, default=False)
parser.add_argument("-i", "--rally_id", type=str, help="ID of the rally configuration to use", required=False)
parser.add_argument("-b", "--backup_path", type=str, help="Folder to store team status backups in", required=False)
parser.add_argument("-a", "--add_date", action='store_true', help="Add a date to the backup folder", required=False, default=False)
args = parser.parse_args()

config_finder = ServerConfigFinder(args.rally_configuration)

configuration = None
if args.rally_id is not None and len(args.rally_id) > 0:
    configuration = config_finder.get_rally_from_id(args.rally_id)
    if configuration is None:
        print("ERROR! No rally configuration with id '{0}' found!".format(args.rally_id))
        sys.exit(1)

if configuration is None:
    if len(config_finder.rally_configs) == 0:
        print("ERROR! No rally configurations found!")
        sys.exit(1)
    elif len(config_finder.rally_configs) == 1:
        configuration = config_finder.rally_configs[0]
    else:
        for i in range(len(config_finder.rally_configs)):
            config = config_finder.rally_configs[i]
            print("{0}: {1}".format(i, config.rally_id))
        while configuration is None:
            s = input("Several configurations found, choose one! > ")
            if s is not None:
                s = s.strip()
                try:
                    index = int(s)
                    if 0 <= index < len(config_finder.rally_configs):
                        configuration = config_finder.rally_configs[index]
                        break
                except ValueError:
                    pass

if configuration is None:
    print("No configuration selected!")
    sys.exit(1)

print("Starting server for '{0}'\n".format(configuration.rally_id))


class ConnectionListener(threading.Thread):
    def __init__(self, host, port, main_server):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.main_server = main_server

    def run(self):
        print("Serving a rally at {0}:{1}".format(self.host, self.port))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            while True:
                s.listen()
                conn, addr = s.accept()
                #print("{0}: {1} / {2}".format(self.port, conn, addr))
                connection_handler = IncomingConnectionHandler(conn, addr, self.main_server)
                connection_handler.start()


backup_path = args.backup_path
if backup_path is not None:
    if not os.path.isdir(backup_path):
        print("Invalid backup path!")
        sys.exit(1)
    if args.add_date:
        backup_path = os.path.abspath(os.path.join(backup_path, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")))
        if not os.path.exists(backup_path):
            os.mkdir(backup_path)
else:
    backup_path = os.path.join(os.getcwd(), "backup")
    if not os.path.exists(backup_path):
        os.mkdir(backup_path)
    if not os.path.exists(backup_path):
        print("Unable to create the backup directory")
        sys.exit(1)
    backup_path = os.path.join(backup_path, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    if not os.path.exists(backup_path):
        os.mkdir(backup_path)
    if not os.path.exists(backup_path):
        print("Unable to create the session backup directory")
        sys.exit(1)
print("Using {0} as backup dir".format(backup_path))

main_server = MainServer(configuration, backup_path)
normal = ConnectionListener(configuration.server_host, configuration.server_port, main_server)
normal.start()
normal.join()
