import argparse

from server.server_config import ServerRallyConfig

parser = argparse.ArgumentParser(description='Help calculating frame from distance')
parser.add_argument("-r", "--rally_configuration", type=str, help="Path to the rally configuration to use", required=True)
args = parser.parse_args()
rally_configuration = ServerRallyConfig(args.rally_configuration)
track_information = rally_configuration.track_information
#print(track_information)

section = track_information.get_section(6)
print(section.calculate_default_video_frame_from_distance(5439.22))
print(section.calculate_default_video_distance_from_frame(11215))
