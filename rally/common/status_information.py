from rally.common.rebuses import RebusStatuses
from rally.protocol import clientprotocol_pb2


class Player:
    def __init__(self, name, user_id):
        self.name = name
        self.user_id = user_id


class Plate:
    def __init__(self, section, index, answer):
        self.section = section
        self.index = index
        self.answer = answer

    def equals(self, other):
        return self.section == other.section and \
               self.index == other.index and \
               self.answer == other.answer


class Photo(Plate):
    def __init__(self, section, index, answer):
        Plate.__init__(self, section, index, answer)


class RebusSolution:
    def __init__(self, solution):
        self.section = solution.section
        self.solution = solution.solution
        self.east = solution.east
        self.north = solution.north
        self.target_description = solution.target_description
        self.target_east = solution.target_east
        self.target_north = solution.target_north
        self.target_picture = solution.target_picture


class StatusInformation:
    def __init__(self, track_information=None):
        self.username = ""
        self.user_id = 0
        self.speed = 0.0
        self.stopped = False
        self.looking_for_rebus = False
        self.rebus_solutions_locked = False
        self.distance = 0.0
        self.rally_stage = clientprotocol_pb2.ServerPositionUpdate.NOT_STARTED
        self.rally_is_started = False
        self.afternoon_is_started = False
        self.current_section = 1
        if track_information is not None:
            self.current_section = track_information.start_section
        self.seating = []
        for i in range(0, 10):
            self.seating.append(Player("", 0))
        self.rebus_statuses = RebusStatuses()
        self.force_update = False

        self.plate_answers = []
        self.plate_answers_seq = 0
        self.photo_answers = []
        self.photo_answers_seq = 0
        self.rebus_answers = {}
        self.rebus_solutions = {}
        self.extra_puzzles = {}
        self.driving_message = ""

    def get_my_seat(self):
        for i in range(1, 10):
            if self.seating[i] is not None:
                if self.seating[i].user_id == self.user_id:
                    return i
        return 0

    def update_pos(self, pos_update):
        if pos_update.HasField("speed"):
            self.speed = pos_update.speed
        if pos_update.HasField("stopped"):
            self.stopped = pos_update.stopped
        if pos_update.HasField("distance"):
            self.distance = pos_update.distance
        if pos_update.HasField("current_section"):
            self.current_section = pos_update.current_section
        if pos_update.HasField("rally_stage"):
            self.rally_stage = pos_update.rally_stage
        if pos_update.HasField("looking_for_rebus"):
            self.looking_for_rebus = pos_update.looking_for_rebus
        if pos_update.HasField("rally_started"):
            self.rally_is_started = pos_update.rally_started
        if pos_update.HasField("afternoon_started"):
            self.afternoon_is_started = pos_update.afternoon_started
        self.force_update = False
        if pos_update.HasField("force_update"):
            self.force_update = pos_update.force_update

    def update_status(self, status_update):
        if status_update.HasField("pos_update"):
            self.update_pos(status_update.pos_update)
        if status_update.HasField("bus_seating"):
            self.update_seating(status_update.bus_seating)
        if status_update.HasField("rebus_list"):
            self.update_rebus_list(status_update.rebus_list)
        if status_update.HasField("photo_answers"):
            self.update_photo_status(status_update.photo_answers)
        if status_update.HasField("plate_answers"):
            self.update_plate_status(status_update.plate_answers)
        if status_update.HasField("rebus_answers"):
            self.update_rebus_status(status_update.rebus_answers)
        if status_update.HasField("rebus_solutions"):
            self.update_rebus_solutions(status_update.rebus_solutions)
        if status_update.HasField("extra_puzzles"):
            self.update_extra_puzzles(status_update.extra_puzzles)
        if status_update.HasField("driving_message"):
            self.update_driving_message(status_update.driving_message)

    def update_seating(self, seating_update):
        for i in range(0, 10):
            self.seating[i] = Player("", 0)

        # print("Update status")
        # if seating_update.HasField("bus_seat_allocations"):
        for seating in seating_update.bus_seat_allocations:
            # print(seating)
            if seating.HasField("seat_index"):
                index = seating.seat_index
                if 0 < index < 10:
                    name = ""
                    user_id = 0
                    if seating.HasField("player_name"):
                        name = seating.player_name
                    if seating.HasField("player_id"):
                        user_id = seating.player_id
                    self.seating[index] = Player(name, user_id)
                    # print("{0}: {1}".format(index, name))

    def update_rebus_list(self, rebus_list):
        for rebus in rebus_list.rebuses:
            rs = self.rebus_statuses.get_rebus_number(rebus.section)
            txt = None
            if rebus.HasField("rebus_text"):
                txt = rebus.rebus_text
            extra = None
            if rebus.HasField("extra_text"):
                extra = rebus.extra_text
            rs.give_rebus(rebus.type, txt, extra)

    def update_plate_status(self, plate_answers_up):
        plate_answers = []
        for plate in plate_answers_up.plate_answers:
            s = None
            if plate.HasField("answer"):
                s = plate.answer
            p = Plate(plate.section_number, plate.section_index, s)
            plate_answers.append(p)
        if not self.compare_plate_or_photo_lists(self.plate_answers, plate_answers):
            self.plate_answers_seq += 1
            self.plate_answers = plate_answers

    def update_photo_status(self, photo_answers_up):
        photo_answers = []
        for photo in photo_answers_up.photo_answers:
            s = None
            if photo.HasField("answer"):
                s = photo.answer
            p = Photo(photo.section_number, photo.section_index, s)
            photo_answers.append(p)
        if not self.compare_plate_or_photo_lists(self.photo_answers, photo_answers):
            self.photo_answers_seq += 1
            self.photo_answers = photo_answers

    def update_rebus_status(self, rebus_answers):
        for answer in rebus_answers.rebus_answers:
            section = answer.section_number
            self.rebus_answers[section] = answer.answer

    def update_rebus_solutions(self, rebus_solutions):
        self.rebus_solutions_locked = rebus_solutions.locked
        for solution in rebus_solutions.rebus_solutions:
            rs = RebusSolution(solution)
            self.rebus_solutions[rs.section] = rs

    def update_extra_puzzles(self, extra_puzzles):
        for extra_puzzle in extra_puzzles.extra_puzzles:
            if extra_puzzle.HasField("puzzle_id"):
                id = extra_puzzle.puzzle_id
                opened = False
                if extra_puzzle.HasField("opened"):
                    opened = extra_puzzle.opened
                if opened:
                    instructions = "Öppnat! Men inga instruktioner tillgängliga..."
                    if extra_puzzle.HasField("instructions"):
                        instructions = extra_puzzle.instructions
                    self.extra_puzzles[id] = instructions

    def update_driving_message(self, driving_message):
        if driving_message.HasField("message"):
            self.driving_message = driving_message.message

    def compare_plate_or_photo_lists(self, l1, l2):
        if len(l1) != len(l2):
            return False
        for i in range(0, len(l1)):
            if not l1[i].equals(l2[i]):
                return False
        return True
