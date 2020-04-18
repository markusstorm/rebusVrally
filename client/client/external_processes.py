import os
import subprocess
import sys


class ProcessTemplate:
    def __init__(self, running_as_exe, client_udp_port, rally_conf, data_path, user_id, my_index, title, program, valid_seats):
        self.running_as_exe = running_as_exe
        self.client_udp_port = client_udp_port
        self.rally_conf = rally_conf
        self.data_path = data_path
        self.user_id = user_id
        self.my_index = my_index
        self.title = title
        self.program = program
        self.valid_seats = valid_seats

    def start_process(self, seat_index):
        if seat_index not in self.valid_seats:
            return None
        if self.running_as_exe:
            parts = self.program.split("/")
            program = parts[-1].replace(".py", ".exe")
            args = [program, "-p", str(self.client_udp_port), "-c", str(self.my_index),
                    "-u", str(self.user_id), "-r", self.rally_conf, "-d", self.data_path]
            working_dir = os.getcwd()
        else:
            args = [sys.executable, self.program, "-p", str(self.client_udp_port), "-c", str(self.my_index),
                    "-u", str(self.user_id), "-r", self.rally_conf, "-d", self.data_path]
            working_dir = os.path.dirname(os.path.abspath(os.path.join(os.getcwd(), self.program)))

        self.adjust_arguments(args)
        print("Starting program: {0}".format(args))

        theproc = subprocess.Popen(args, cwd=working_dir)
        return theproc

    def adjust_arguments(self, args):
        pass


class PhotoSheetTemplate(ProcessTemplate):
    def __init__(self, running_as_exe, client_udp_port, rally_conf, data_path, user_id, my_index, title, program, valid_seats, index):
        ProcessTemplate.__init__(self, running_as_exe, client_udp_port, rally_conf, data_path, user_id, my_index, title, program, valid_seats)
        self.index = index

    def adjust_arguments(self, args):
        args.append("-i")
        args.append(str(self.index))


class VideoProcessTemplate(ProcessTemplate):
    def __init__(self, running_as_exe, client_udp_port, rally_conf, data_path, user_id, my_index, title, program, valid_seats, direction):
        ProcessTemplate.__init__(self, running_as_exe, client_udp_port, rally_conf, data_path, user_id, my_index, title, program, valid_seats)
        self.direction = direction

    def adjust_arguments(self, args):
        args.append("-v")
        args.append(str(self.direction))


class SubProcesses:
    def __init__(self, subprocess_communicator, rally_configuration, running_as_exe, config_file):
        self.running_as_exe = running_as_exe
        self.subprocess_communicator = subprocess_communicator
        self.rally_configuration = rally_configuration
        data_path = rally_configuration.data_path
        self.started_processes = []
        udp_port = subprocess_communicator.udp_port
        #rally_conf = rally_configuration.file_name
        user_id = self.subprocess_communicator.server_connection.status_information.user_id
        self.process_templates = [
            ProcessTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 1, "Steering wheel", "../steering/steering.py", [1]),
            VideoProcessTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 2, "Front video", "../out_the_window/movie_window.py", [1, 2, 3, 5, 8], "front"),
            VideoProcessTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 3, "Left video", "../out_the_window/movie_window.py", [4, 7], "left"),
            VideoProcessTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 4, "Right video", "../out_the_window/movie_window.py", [6, 9], "right"),
            ProcessTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 10, "Rebus list", "../fishbone/fishbone.py", [5]),
            ProcessTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 13, "Solve Rebus", "../solve_rebus/solve_rebus.py", [5])
            #ProcessTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 11, "Photo Answers", "../photo_report/photo_report.py", [5]),
            #ProcessTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 12, "Rebus Answers", "../rebus_answers/rebus_answers.py", [5]),
            # PhotoSheetTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 5, "Photo sheet front", "../photo_sheet/photosheet.py", [1, 2, 3], 1),
            # PhotoSheetTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 6, "Photo sheet middle1", "../photo_sheet/photosheet.py", [4, 5, 6], 2),
            # PhotoSheetTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 7, "Photo sheet middle2", "../photo_sheet/photosheet.py", [4, 5, 6], 3),
            # PhotoSheetTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 8, "Photo sheet back1", "../photo_sheet/photosheet.py", [7, 8, 9], 4),
            # PhotoSheetTemplate(running_as_exe, udp_port, config_file, data_path, user_id, 9, "Photo sheet back2", "../photo_sheet/photosheet.py", [7, 8, 9], 5),
        ]

    def start_processes(self, seat_index):
        for template in self.process_templates:
            proc = template.start_process(seat_index)
            if proc is not None:
                self.started_processes.append(proc)
        # TODO: check success

    def stop_processes(self):
        self.subprocess_communicator.clear_clients()
        for proc in self.started_processes:
            proc.terminate()
        self.started_processes = []
