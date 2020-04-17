import datetime
import json
import os
import random
from functools import partial

from rally.common.rebuses import RebusStatuses
from rally.common.status_information import Plate, Photo
from rally.protocol import clientprotocol_pb2
from server.minibus import MiniBus
from server.server_config import RebusConfig


class RebusSolution:
    def __init__(self, rc):
        self.rc = rc
        self.target_description = ""
        self.target_east = 0
        self.target_north = 0
        self.target_picture = ""
        self.test_count = 0
        self.description = ""

    def to_json(self):
        json = {}
        json["rc-section"] = self.rc.section
        json["target_description"] = self.target_description
        json["target_east"] = self.target_east
        json["target_north"] = self.target_north
        json["target_picture"] = self.target_picture
        json["test_count"] = self.test_count
        json["description"] = self.description
        return json
        # TODO: when reading back: find the correct rc object, do NOT create a new one!

    def compare(self, solution_req):
        self.test_count += 1

        if self.rc.solution.casefold() != solution_req.answer.casefold():
            self.description = "\"{0}\" är inte rätt lösning".format(solution_req.answer)
            return False

        east_min = max(0, self.rc.east - 1)
        east_max = self.rc.east + 1
        if not (east_min <= solution_req.map_east <= east_max):
            self.description = "Lösningen ligger inte på {0} öst, {1} nord på kartan".format(solution_req.map_east, solution_req.map_north)
            return False
            
        north_min = max(0, self.rc.north - 1)
        north_max = self.rc.north + 1
        if not (north_min <= solution_req.map_north <= north_max):
            self.description = "Lösningen ligger inte på {0} öst, {1} nord på kartan".format(solution_req.map_east, solution_req.map_north)
            return False

        self.target_description = self.rc.target_description
        self.description = self.target_description
        self.target_east = self.rc.target_east
        self.target_north = self.rc.target_north
        self.target_picture = self.rc.target_picture
        return True

    def pack(self):
        rs = clientprotocol_pb2.RebusSolution()
        rs.section = self.rc.section
        rs.solution = self.rc.solution
        rs.east = self.rc.east
        rs.north = self.rc.north
        rs.target_description = self.description
        rs.target_east = self.target_east
        rs.target_north = self.target_north
        rs.target_picture = self.target_picture
        return rs


class TeamServer:
    """ Keeps track of the progress of each team """

    def __init__(self, teamname, team_number, rally_configuration, main_server, difficulty, backup_path):
        self.main_server = main_server
        self.rally_configuration = rally_configuration
        self.teamname = teamname
        self.team_number = team_number
        self.difficulty = difficulty
        self.backup_path = os.path.join(backup_path, str(team_number))
        os.mkdir(self.backup_path)
        self.clients = []
        self.changed = True
        self.update_counter = 0
        self.rally_stage = clientprotocol_pb2.ServerPositionUpdate.RallyStage.NOT_STARTED
        self.looking_for_rebus = False
        self.lock_time = None
        self.start_time = datetime.datetime.now() # TODO: make sure to restore when reading from json
        self.lunch_time = None
        self.found_goal_time = None
        self.goal_time = None
        self.latest_backup_contents = ""

        #self.status_information = StatusInformation(rally_configuration.track_information)
        # TODO: use StatusInformation for seating and other position info?

        self.rebus_statuses = RebusStatuses(rally_configuration.rebus_configs)

        self.minibus = MiniBus(rally_configuration.track_information, self.difficulty)
        self.plate_answers = []
        self.photo_answers = []
        self.rebus_answers = {}
        self.rebus_solutions = {}

    @staticmethod
    def date_to_json(date):
        if date is None:
            return None
        return date.strftime("%Y-%m-%d %H:%M:%S")

    def to_json(self, verbose=True):
        json = {}
        json["team-name"] = self.teamname
        json["team-number"] = self.team_number
        json["rally-stage"] = self.rally_stage
        json["minibus"] = self.minibus.to_json(verbose)
        json["rebus-statuses"] = self.rebus_statuses.to_json()
        json["start-time"] = TeamServer.date_to_json(self.start_time)
        json["lunch-time"] = TeamServer.date_to_json(self.lunch_time) # can be None
        json["found-goal-time"] = TeamServer.date_to_json(self.found_goal_time) # can be None
        json["goal-time"] = TeamServer.date_to_json(self.goal_time) # can be None
        solution_json = {}
        for section in self.rebus_solutions:
            rebus_solution = self.rebus_solutions[section]
            if rebus_solution is not None:
                solution_json[section] = rebus_solution.to_json()
        json["rebus-solutions"] = solution_json
        return json

    def backup_status_to_disk(self):
        print("backup_status_to_disk")
        json_str = json.dumps(self.to_json(False))
        if json_str != self.latest_backup_contents:
            self.latest_backup_contents = json_str
            new_backup_file = os.path.join(self.backup_path, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
            with open(new_backup_file, "w") as f:
                f.write(json_str)

    def addClient(self, client):
        self.clients.append(client)

    def findClient(self, user_id):
        for client in self.clients:
            if client.user_id == user_id:
                return client
        return None

    def remove_client(self, user_id):
        self.minibus.remove_user(user_id)
        client = self.findClient(user_id)
        if client is not None:
            self.clients.remove(client)

    def send_messages(self, message):
        server_to_client = clientprotocol_pb2.ServerToClient()
        server_to_client.broadcast_message.SetInParent()
        bc_message = server_to_client.broadcast_message
        bc_message.message = message
        bc_message.date_time = datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
        self.send(server_to_client)

    def send(self, server_to_client):
        for client in self.clients:
            client.send(server_to_client)

    def select_seat(self, select_seat_message):
        if self.minibus.select_seat(select_seat_message, self):
            self.changed = True

    def update_pos_from_driver(self, pos_update):
        self.minibus.update_pos_from_driver(pos_update)

    def give_rebus_data(self, section, rebus_type, txt, extra):
        self.rebus_statuses.give_rebus(section, rebus_type, txt, extra)
        self.changed = True

    def log_action(self, message):
        # TODO: to more permanent storage
        print("LOG ACTION " + datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + ": " + message)

    def open_rebus_solution(self, client_message):
        section = client_message.section
        #TODO: validate section based on configuration
        if 0 < section < 9:
            rc = self.rally_configuration.get_rebus_config(section)
            if rc is not None:
                if client_message.open_help:
                    self.log_action("{0} requested HELP for rebus {1} to be opened".format(client_message.user_id, section))
                    self.give_rebus_data(section, RebusConfig.HELP, rc.help, None)
                elif client_message.open_solution:
                    self.log_action("{0} requested SOLUTION for rebus {1} to be opened".format(client_message.user_id, section))
                    extra = "{0} öst, {1} nord".format(rc.east, rc.north)
                    self.give_rebus_data(section, RebusConfig.SOLUTION, rc.solution, extra)

    def set_photo_answer(self, answer_message):
        section = answer_message.section
        index = answer_message.index
        # TODO: validate section based on configuration
        if 0 < section < 9 and 0 <= index < 10:
            if answer_message.HasField("answer") and answer_message.answer > 0:
                obj = None
                for photo in self.photo_answers:
                    if photo.section == section and photo.index == index:
                        obj = photo
                        break
                if obj is None:
                    obj = Photo(section, index, "")
                    self.photo_answers.append(obj)
                obj.answer = answer_message.answer
                self.changed = True
            else:
                for photo in self.photo_answers:
                    if photo.section == section and photo.index == index:
                        self.photo_answers.remove(photo)
                        self.changed = True
                        break

    def set_plate_answer(self, answer_message):
        section = answer_message.section
        index = answer_message.index
        # TODO: validate section based on configuration
        if 0 < section < 9 and 0 <= index < 10:
            if answer_message.HasField("answer") and len(answer_message.answer.strip()) > 0:
                obj = None
                for plate in self.plate_answers:
                    if plate.section == section and plate.index == index:
                        obj = plate
                        break
                if obj is None:
                    obj = Plate(section, index, "")
                    self.plate_answers.append(obj)
                obj.answer = answer_message.answer.strip().upper()
                self.changed = True
            else:
                for plate in self.plate_answers:
                    if plate.section == section and plate.index == index:
                        self.plate_answers.remove(plate)
                        self.changed = True
                        break

    def set_rebus_answer(self, answer_message):
        section = answer_message.section
        # TODO: validate section based on configuration
        if 0 < section < 9:
            if answer_message.HasField("answer") and len(answer_message.answer.strip()) > 0:
                txt = answer_message.answer
                self.rebus_answers[section] = txt
                self.changed = True
            else:
                self.rebus_answers[section] = ""
                self.changed = True

    def handle_found_lunch(self, rebus_place, rc):
        self.lunch_time = datetime.datetime.now()
        self.rally_stage = clientprotocol_pb2.ServerPositionUpdate.RallyStage.AT_LUNCH
        if self.minibus.current_section != rebus_place.next_section:
            self.minibus.warp(rebus_place.next_section, 0)
        for message in self.rally_configuration.lunch_messages:
            self.send_messages(message)

    def handle_found_goal(self, rebus_place, rc):
        self.found_goal_time = datetime.datetime.now()
        self.rally_stage = clientprotocol_pb2.ServerPositionUpdate.RallyStage.AT_END
        if self.minibus.current_section != rebus_place.next_section:
            self.minibus.warp(rebus_place.next_section, 0)
        for message in self.rally_configuration.at_end_messages:
            self.send_messages(message)

    def end_rally(self):
        self.goal_time = datetime.datetime.now()
        self.rally_stage = clientprotocol_pb2.ServerPositionUpdate.RallyStage.ENDED
        for message in self.rally_configuration.end_messages:
            self.send_messages(message)

    def rally_is_started(self):
        pass

    def search_for_rebus_result(self, rebus):
        print("Team {0} rebus result arrived".format(self.teamname))
        self.looking_for_rebus = False
        if rebus is not None:
            print("Get rebus {0}".format(rebus.number))
            rc = self.rally_configuration.get_rebus_config(rebus.number)
            if rc is not None:
                print("...and they found a rebus!")
                self.send_messages("Hittade rebus {0}! Titta i rebus-arket!".format(rebus.number))

                self.give_rebus_data(rc.section, RebusConfig.NORMAL, rc.normal, None)
            else:
                self.send_messages("Hittade tyvärr ingen rebuskontroll här. Åk till någon annan plats och leta vidare!")
        else:
            self.send_messages("Hittade tyvärr ingen rebuskontroll här. Åk till någon annan plats och leta vidare!")

    def search_for_rebus(self):
        if self.looking_for_rebus:
            return
        if abs(self.minibus.speed) > 0.001:
            return
        self.looking_for_rebus = True
        section = self.rally_configuration.track_information.get_section(self.minibus.current_section)
        if section is not None:
            rebus_place = section.find_nearby_rebus_place(self.minibus.distance)
            search_time = 15 + random.randrange(0, 45) # It can take up to 1 minute to find the rebus
            #DEBUG!
            print("TODO: remove debug time for searching for rebus!")
            search_time = 1

            if rebus_place is None:
                print("Warning: no rebus at that place...")
            else:
                rc = self.rally_configuration.get_rebus_config(rebus_place.number)
                if rc is None:
                    self.send_messages("Error in configuration, can't find rebus {0}!".format(rebus_place.number))
                    return
                elif rc.is_lunch:
                    print("Lunch!")
                    self.send_messages("Lunch!")
                    self.handle_found_lunch(rebus_place, rc)
                    self.looking_for_rebus = False
                    return
                elif rc.is_goal:
                    print("Mål!")
                    self.send_messages("Mål!")
                    self.handle_found_goal(rebus_place, rc)
                    self.looking_for_rebus = False
                    return

            print("Team {0} looking for a rebus with timeout {1}".format(self.teamname, search_time))
            self.main_server.scheduler.schedule_action(search_time, partial(self.search_for_rebus_result, rebus_place))
            self.send_messages("Har skickat ut en spanare för att leta efter en rebus här, det kan ta upp till en minut...")

    def is_rebus_testing_locked(self):
        if self.lock_time is None:
            return False
        diff = datetime.datetime.now() - self.lock_time
        return int(diff.total_seconds()) < 60

    def test_rebus_solution(self, solution_req):
        ok_to_continue = not self.is_rebus_testing_locked()
        if not ok_to_continue:
            self.log_warning("Asking to test rebus solution at {0} but is locked from {1}+60 seconds".format(datetime.datetime.now(), self.lock_time))
            return
        self.lock_time = datetime.datetime.now()
        rc = self.rally_configuration.get_rebus_config(solution_req.section)
        if rc is None:
            print("ERROR! No rebus for section {0}".format(solution_req.section))
            return

        rebus_solution = None
        if solution_req.section in self.rebus_solutions:
            rebus_solution = self.rebus_solutions[solution_req.section]
        else:
            rebus_solution = RebusSolution(rc)
            self.rebus_solutions[solution_req.section] = rebus_solution

        result = rebus_solution.compare(solution_req)
        self.log_action("Testing rebus {0} for the {1}th time with result: {2}".format(rebus_solution.rc.section, rebus_solution.test_count, result))
        self.changed = True

        if result:
            # The correct solution was found, now the team can move on
            if rc.is_start:
                self.handle_solved_morning_rebus()
            if rc.is_lunch:
                self.handle_solved_lunch_rebus()

    def handle_solved_morning_rebus(self):
        self.rally_stage = clientprotocol_pb2.ServerPositionUpdate.RallyStage.MORNING

    def handle_solved_lunch_rebus(self):
        self.rally_stage = clientprotocol_pb2.ServerPositionUpdate.RallyStage.AFTERNOON

    def fill_plate_update(self, plate_up):
        for plate in self.plate_answers:
            answer = clientprotocol_pb2.PlateAnswer()
            answer.section_number = plate.section
            answer.section_index = plate.index
            answer.answer = plate.answer
            plate_up.plate_answers.extend([answer])

    def fill_photo_update(self, photo_up):
        for photo in self.photo_answers:
            answer = clientprotocol_pb2.PhotoAnswer()
            answer.section_number = photo.section
            answer.section_index = photo.index
            answer.answer = photo.answer
            photo_up.photo_answers.extend([answer])

    def fill_rebus_update(self, rebus_up):
        for section in self.rebus_answers:
            answer = clientprotocol_pb2.RebusAnswer()
            answer.section_number = section
            answer.answer = self.rebus_answers[section]
            rebus_up.rebus_answers.extend([answer])

    def fill_rebus_solutions(self, rs):
        rs.locked = self.is_rebus_testing_locked()
        for solution in self.rebus_solutions.values():
            obj = solution.pack()
            rs.rebus_solutions.extend([obj])

    def send_updates_to_clients(self):
        # print("Send updates to clients")
        # Always send position update
        server_to_client = clientprotocol_pb2.ServerToClient()
        server_to_client.status_update.SetInParent()
        status_update = server_to_client.status_update
        status_update.pos_update.SetInParent()
        pu = status_update.pos_update
        self.minibus.fill_pos_update(pu)
        pu.rally_stage = self.rally_stage
        pu.looking_for_rebus = self.looking_for_rebus
        pu.rally_started = self.main_server.rally_is_started
        pu.afternoon_started = self.main_server.afternoon_is_started

        self.update_counter += 1
        send_more_updates = self.changed or self.update_counter > 10
        if send_more_updates:
            self.changed = False
            self.update_counter = 0

            status_update.bus_seating.SetInParent()
            bus_seating = status_update.bus_seating
            self.minibus.fill_seating_update(bus_seating)

            status_update.rebus_list.SetInParent()
            self.rebus_statuses.fill_rebus_list(status_update.rebus_list)

            status_update.plate_answers.SetInParent()
            self.fill_plate_update(status_update.plate_answers)

            status_update.photo_answers.SetInParent()
            self.fill_photo_update(status_update.photo_answers)

            status_update.rebus_answers.SetInParent()
            self.fill_rebus_update(status_update.rebus_answers)

            status_update.rebus_solutions.SetInParent()
            self.fill_rebus_solutions(status_update.rebus_solutions)

        self.send(server_to_client)
