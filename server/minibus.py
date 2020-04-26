from rally.common.status_information import Player
from rally.common.track_information import Turn
from rally.protocol import clientprotocol_pb2, serverprotocol_pb2


class MiniBus:
    def __init__(self, track_information, difficulty, teamserver):
        self.teamserver = teamserver
        self.track_information = track_information
        self.difficulty = difficulty
        self.stopped = True
        self.speed = 0
        self.current_section = track_information.start_section
        self.distance = track_information.get_section(self.current_section).get_start_distance()
        self.indicator_light = clientprotocol_pb2.ClientPositionUpdate.NONE
        self.force_update = False
        self.incorrect_turns = {}

        self.seating = []
        for i in range(0, 10):
            self.seating.append(None)

    def to_json(self, verbose):
        json = {}
        json["current_section"] = self.current_section
        json["distance"] = self.distance
        json["incorrect_turns"] = self.incorrect_turns
        if verbose:
            json["speed"] = self.speed
            # Skip seating when reading back, people will have to reconnect
            seating = {}
            json["seating"] = seating
            for i in range(1, 10):
                player = self.seating[i]
                if player is not None:
                    # Skip user id when reading back
                    seating[i] = {"name": player.name, "id": player.user_id}
        return json

    def restore_from_json(self, _json):
        if "current_section" in _json:
            self.current_section = _json["current_section"]
        if "distance" in _json:
            self.distance = _json["distance"]
        if "incorrect_turns" in _json:
            self.incorrect_turns = _json["incorrect_turns"]

    def warp(self, section_number, frame):
        print("Warping to section {0} frame {1}".format(section_number, frame))
        self.speed = 0
        self.stopped = True
        self.current_section = section_number
        section = self.track_information.get_section(self.current_section)
        self.distance = section.calculate_default_video_distance_from_frame(frame)
        self.force_update = True

    def update_pos_from_driver(self, pos_update):
        section = self.track_information.get_section(self.current_section)
        if pos_update.HasField("speed"):
            self.speed = pos_update.speed
            self.stopped = abs(self.speed) < 0.001
        if pos_update.HasField("delta_distance"):
            self.distance += pos_update.delta_distance
            if self.distance < section.get_start_distance():
                self.distance = section.get_start_distance()
            if self.distance > section.get_default_end_distance():
                self.distance = section.get_default_end_distance()
        if pos_update.HasField("indicator"):
            self.indicator_light = pos_update.indicator

        turn = section.get_correct_turn()
        turning_handled = False
        if turn is not None:
            turn_distance = section.calculate_default_video_distance_from_frame(turn.frame_offset)
            if turn_distance <= self.distance <= turn_distance+100: # TODO: possibly less than 100 meters
                # TODO: Handle when the driver is signalling a turn but it is a wrong turn (TURN_WRONG)
                turning_handled = True
                turn_matched = False
                if turn.direction == Turn.STRAIGHT_AHEAD and self.indicator_light == clientprotocol_pb2.ClientPositionUpdate.NONE:
                    turn_matched = True
                if turn.direction == Turn.TURN_LEFT and self.indicator_light == clientprotocol_pb2.ClientPositionUpdate.LEFT:
                    turn_matched = True
                if turn.direction == Turn.TURN_RIGHT and self.indicator_light == clientprotocol_pb2.ClientPositionUpdate.RIGHT:
                    turn_matched = True
                if self.difficulty == serverprotocol_pb2.LoginRequest.EASY:
                    turn_matched = True
                if turn_matched or turn.automatic:
                    if not self.found_all_checkpoints_in_section(section):
                        if not turn.already_warned_checkpoint:
                            turn.already_warned_checkpoint = True
                            self.teamserver.action_logger.log_warning("Not taking turn to next section {0} because the team hasn't found the rebus checkpoints in this section yet".format(turn.next_section))
                    else:
                        self.current_section = turn.next_section
                        next_section = self.track_information.get_section(turn.next_section)
                        self.distance = next_section.get_start_distance()
                        self.force_update = True
                else:
                    if not turn.already_warned:
                        turn.already_warned = True
                        self.teamserver.action_logger.log_warning("Not taking turn to next section {0} because there is no indicator light".format(turn.next_section))

        if not turning_handled:
            # The above code didn't find a normal turn to handle, so check if the driver has gone too far
            if section.missed_all_turns(self.distance):
                # The team has missed the exit and has ended up at the end of the video
                self.mark_missed_turn(section.section_number, section.get_last_turn())
                # No need to do anything else here, the steering GUI will also tell the driver that he's gone too far

    def found_all_checkpoints_in_section(self, section):
        checkpoints_in_section = []
        for rp in section.rebus_places:
            checkpoints_in_section.append(rp.id)
        found_checkpoints = []
        for team_found in self.teamserver.found_rebus_checkpoints:
            if team_found in checkpoints_in_section:
                found_checkpoints.append(team_found)
        return len(found_checkpoints) == len(checkpoints_in_section)

    def mark_missed_turn(self, section_number, turn):
        # Type is TURN_WRONG or TURN_MISSED
        turn_type_str = Turn.direction_translation_to_string[turn.direction]
        turn_id = "{0}-{1}".format(section_number, turn.frame_offset)
        if turn_id not in self.incorrect_turns:
            self.teamserver.action_logger.log_penalty(5, "{0} turn {1} in section {2}".format(turn_type_str, turn_id, section_number))
        self.incorrect_turns[turn_id] = turn_type_str

    def fill_pos_update(self, pu):
        pu.stopped = self.stopped
        pu.speed = self.speed
        pu.current_section = self.current_section
        pu.distance = self.distance
        if self.force_update:
            pu.force_update = True
        self.force_update = False

    def fill_seating_update(self, bus_seating):
        for i in range(1, 10):
            if self.seating[i] is not None:
                # print("{0}: {1}".format(i, self.seating[i]))
                bsa = clientprotocol_pb2.BusSeatAllocation()
                bsa.seat_index = i
                bsa.player_id = self.seating[i].user_id
                bsa.player_name = self.seating[i].name
                bus_seating.bus_seat_allocations.extend([bsa])

    def remove_user(self, user_id):
        # Emergency stop if the driver quits
        if self.is_driver(user_id):
            self.stopped = True
            self.speed = 0.0
        for i in range(1, 10):
            if self.seating[i] is not None:
                if self.seating[i].user_id == user_id:
                    self.seating[i] = None
                    break

    def is_driver(self, user_id):
        if self.seating[1] is not None:
            return self.seating[1].user_id == user_id
        return False

    def select_seat(self, select_seat_message, teamserver):
        if select_seat_message.HasField("user_id") and select_seat_message.HasField("seat_index"):
            user_id = select_seat_message.user_id
            seat_index = select_seat_message.seat_index
            client = teamserver.findClient(user_id)
            if client is not None:
                # the new seat is not taken?
                if self.seating[seat_index] is None or seat_index == 0:
                    # Remove current seating
                    for i in range(1, 10):
                        if self.seating[i] is None:
                            continue
                        if self.seating[i].user_id == user_id:
                            self.seating[i] = None
                            break
                    if seat_index > 0:
                        self.seating[seat_index] = Player(client.username, user_id)
                    return True
        return False
