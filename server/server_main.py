import argparse
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

HOST = "0.0.0.0"
if args.start_locally or configuration.is_local:
    HOST = "127.0.0.1"
NORMAL_PORT = 63332  # Port to listen on (non-privileged ports are > 1023)
DYNDNS_PORT = 63343


class ConnectionListener(threading.Thread):
    def __init__(self, port, main_server):
        threading.Thread.__init__(self)
        self.port = port
        self.main_server = main_server

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, self.port))
            while True:
                s.listen()
                conn, addr = s.accept()
                #print("{0}: {1} / {2}".format(self.port, conn, addr))
                connection_handler = IncomingConnectionHandler(conn, addr, self.main_server)
                connection_handler.start()


main_server = MainServer(configuration, HOST)
normal = ConnectionListener(NORMAL_PORT, main_server)
normal.start()
if not args.start_locally:
    dyndns = ConnectionListener(DYNDNS_PORT, main_server)
    dyndns.start()
else:
    dyndns = None

normal.join()
if dyndns is not None:
    dyndns.join()
