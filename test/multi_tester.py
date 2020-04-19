import argparse
import signal
import sys
import time

from client.client.external_processes import ProcessTemplate, SubProcessesBase, ProcessTemplateBase
from server.server_config_finder import ServerConfigFinder

parser = argparse.ArgumentParser(description='Starts multiple team tester clients')
parser.add_argument("-r", "--rally_configuration", type=str, help="Path to the rally configuration to use", required=True)
parser.add_argument("-n", "--number_of_teams", type=int, help="Number of teams to simulate, default 1", required=False)
args = parser.parse_args()

config_finder = ServerConfigFinder(args.rally_configuration)
server_configuration = config_finder.rally_configs[0]

number_of_teams = args.number_of_teams
number_of_teams = min(max(1, number_of_teams), 20)

running_as_exe = SubProcessesBase.detect_if_running_as_exe(sys.argv)
sub_processes = SubProcessesBase()


class TestClientProcessTemplate(ProcessTemplateBase):
    def __init__(self, running_as_exe, title, program, configuration_file, team_id):
        ProcessTemplateBase.__init__(self, running_as_exe, title, program)
        self.configuration_file = configuration_file
        self.team_id = team_id

    def build_arguments(self, args):
        args.extend(["-r", self.configuration_file,
                     "-t", str(self.team_id),
                     "-n", str(9)])


for team_number in range(1, number_of_teams+1):
    sub_processes.process_templates.append(TestClientProcessTemplate(running_as_exe, "Title", "team_tester.py", args.rally_configuration, team_number))

sub_processes.start_processes()

terminate = False
def signal_handler(sig, frame):
    global terminate
    terminate = True
    print('Got SIGINT')

signal.signal(signal.SIGINT, signal_handler)

while not terminate:
    time.sleep(1)
