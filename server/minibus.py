from rally.common.status_information import Player
from rally.common.track_information import Turn
from rally.protocol import clientprotocol_pb2, serverprotocol_pb2


class MiniBus:
    def __init__(self, track_information, difficulty):
        self.track_information = track_information
        self.difficulty = difficulty
        self.stopped = True
        self.speed = 0
        self.current_section = track_information.start_section
        self.distance = track_information.get_section(self.current_section).get_start_distance()
        self.indicator_light = clientprotocol_pb2.ClientPositionUpdate.NONE
        self.force_update = False

        self.seating = []
        for i in range(0, 10):
            self.seating.append(None)

    def to_json(self):
        json = {}
        json["speed"] = self.speed #TODO: when reading back, set speed to 0
        json["current_section"] = self.current_section
        json["distance"] = self.distance
        # Skip seating when reading back, people will have to reconnect
        seating = {}
        json["seating"] = seating
        for i in range(1, 10):
            player = self.seating[i]
            if player is not None:
                # Skip user id when reading back
                seating[i] = {"name": player.name}
        return json

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
        # TODO: this just moves the car into the next section automatically, require the user to turn instead
        # TODO: use self.indicator_light instead
        #section = self.track_information.get_section(self.current_section)
        turn = section.get_correct_turn()
        if turn is not None:
            turn_distance = section.calculate_default_video_distance_from_frame(turn.frame_offset)
            if turn_distance <= self.distance <= turn_distance+100:
                turn_matched = False
                if turn.direction == Turn.STRAIGHT_AHEAD and self.indicator_light == clientprotocol_pb2.ClientPositionUpdate.NONE:
                    turn_matched = True
                if turn.direction == Turn.TURN_LEFT and self.indicator_light == clientprotocol_pb2.ClientPositionUpdate.LEFT:
                    turn_matched = True
                if turn.direction == Turn.TURN_RIGHT and self.indicator_light == clientprotocol_pb2.ClientPositionUpdate.RIGHT:
                    turn_matched = True
                if self.difficulty == serverprotocol_pb2.LoginRequest.EASY:
                    turn_matched = True
                if turn_matched:
                    self.current_section = turn.next_section
                    next_section = self.track_information.get_section(turn.next_section)
                    self.distance = next_section.get_start_distance()
                    self.force_update = True
                else:
                    print("Not taking turn to next section because there is no indicator light")

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
