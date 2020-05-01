import argparse
import os
import shutil
import subprocess
import sys

import dirsync

parser = argparse.ArgumentParser(description='Build distribution')
parser.add_argument("-u", "--allow_unclean", action='store_true', help="Allow an unclean build", required=False, default=False)
parser.add_argument("-b", "--skip_build", action='store_true', help="Skip the pyinstaller build phase", required=False, default=False)
args = parser.parse_args()


def build_pyinstaller(build_folder, local_path):
    python_command = sys.executable
    python_dir = os.path.dirname(python_command)
    pyinstaller = os.path.abspath(os.path.join(python_dir, "Scripts/pyinstaller.exe"))
    args = [pyinstaller, os.path.abspath(local_path)]
    print("Building PyInstaller for {0}...".format(local_path))
    builder = subprocess.Popen(args, cwd=build_folder)
    builder.communicate()
    return_code = builder.returncode
    #print("Return code: {0}".format(return_code))
    if return_code != 0:
        print("Unable to build {0}".format(local_path))
        raise RuntimeError("Unable to build {0}".format(local_path))

if os.path.exists("build") and not args.allow_unclean:
    print("ERROR! Build folder already exists!")
    sys.exit(1)

if not os.path.exists("build"):
    os.mkdir("build")

build_folder = os.path.abspath("build")
source_folder = os.path.abspath(os.path.join(os.path.abspath(os.getcwd()), ".."))

if not args.skip_build:
    build_pyinstaller(build_folder, "../client/client/client_main.py")
    build_pyinstaller(build_folder, "../client/solve_rebus/solve_rebus.py")
    build_pyinstaller(build_folder, "../client/out_the_window/movie_window.py")
    build_pyinstaller(build_folder, "../client/steering/steering.py")
    build_pyinstaller(build_folder, "../client/fishbone/fishbone.py")
    #build_pyinstaller(build_folder, "../server/server_main.py")

target_dir = os.path.abspath(os.path.join(build_folder, "rebusVrally"))
if os.path.exists(target_dir) and not args.allow_unclean:
    print("ERROR! Target folder already exists!")
    sys.exit(1)

if not os.path.exists(target_dir):
    os.mkdir(target_dir)

build_dist = os.path.abspath(os.path.join(build_folder, "dist"))
def sync_folder(folder, target):
    _from = os.path.abspath(os.path.join(build_dist, folder))
    dirsync.sync(_from, target, "sync")

def sync_source_folder(folder, target, ignore=None):
    _from = os.path.abspath(os.path.join(source_folder, folder))
    print("Sync source {0} to {1}".format(_from, target))
    if ignore is None:
        dirsync.sync(_from, target, "sync")
    else:
        dirsync.sync(_from, target, "sync", exclude=ignore)


sync_folder("client_main", target_dir)
sync_folder("fishbone", target_dir)
sync_folder("movie_window", target_dir)
sync_folder("solve_rebus", target_dir)
sync_folder("steering", target_dir)

client_conf_folder = os.path.abspath(os.path.join(target_dir, "configs"))
if not os.path.exists(client_conf_folder):
    os.mkdir(client_conf_folder)

#sync_source_folder("configs", client_conf_folder, (r'.*\.dat$', r'vt2020',))
sync_source_folder("configs", client_conf_folder, (r'.*\.dat$',))

# ----------------------------------------------------------
# Server
# server_folder = os.path.abspath(os.path.join(target_dir, "server"))
# if not os.path.exists(server_folder):
#     os.mkdir(server_folder)
# sync_folder("server_main", server_folder)
#
#
# server_conf_folder = os.path.abspath(os.path.join(server_folder, "configs"))
# if not os.path.exists(server_conf_folder):
#     os.mkdir(server_conf_folder)
#
# sync_source_folder("server/configs", server_conf_folder)


def remove_file(file):
    file = os.path.abspath(os.path.join(target_dir, file))
    if os.path.exists(file):
        print("Remove {0}".format(file))
        os.remove(file)
        print("Removed {0}".format(file))


def adjust_filename(_from, to, remove_target_first_if_both_exists=True):
    _from = os.path.abspath(os.path.join(target_dir, _from))
    to = os.path.abspath(os.path.join(target_dir, to))
    if not os.path.exists(_from):
        raise RuntimeError("Unable to find the file {0} to rename to {1}".format(_from, to))
    if os.path.exists(to):
        if not remove_target_first_if_both_exists:
            raise RuntimeError("The file {1} already exists that {0} shall be renamed to".format(_from, to))
        else:
            remove_file(to)
    os.rename(_from, to)
    print("Renamed {0}".format(_from))

def copy_source_file(file, to_dir, remove_target_first_if_both_exists=True):
    _from = os.path.abspath(os.path.join(source_folder, file))
    to_dir = os.path.abspath(os.path.join(target_dir, to_dir))
    to = os.path.abspath(os.path.join(to_dir, os.path.basename(_from)))
    if not os.path.exists(_from):
        raise RuntimeError("Unable to find the file {0} to copy to {1}".format(_from, to))
    if os.path.exists(to):
        if not remove_target_first_if_both_exists:
            raise RuntimeError("The file {1} already exists that {0} shall be copied to".format(_from, to))
        else:
            remove_file(to)
    shutil.copy(_from, to)
    print("Copied {0}".format(_from))


adjust_filename("client_main.exe", "rebusVrally.exe", True)
adjust_filename("client_main.exe.manifest", "rebusVrally.exe.manifest", True)
remove_file("configs/demo_rally/data/put_the_videos_here.txt")
remove_file("config.ini")

copy_source_file("client/client/minibus.png", target_dir)
copy_source_file("client/steering/backup.png", target_dir)
copy_source_file("client/steering/blinkers_left_off_70.png", target_dir)
copy_source_file("client/steering/blinkers_left_on_70.png", target_dir)
copy_source_file("client/steering/blinkers_right_off_70.png", target_dir)
copy_source_file("client/steering/blinkers_right_on_70.png", target_dir)
copy_source_file("client/steering/gas_and_brake.png", target_dir)
copy_source_file("client/steering/speed_frame.png", target_dir)
