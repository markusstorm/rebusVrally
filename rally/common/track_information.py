import os
import xml.etree.ElementTree as ET


class Turn:
    TURN_LEFT = 1
    TURN_RIGHT = 2
    STRAIGHT_AHEAD = 3

    def __init__(self, turn):
        direction_translation = {"left": Turn.TURN_LEFT, "right": Turn.TURN_RIGHT, "straight": Turn.STRAIGHT_AHEAD}
        self.direction = direction_translation[turn.attrib["direction"]]
        self.frame_offset = int(turn.attrib["frame_offset"])
        self.description = None
        if "description" in turn.attrib:
            self.description = turn.attrib["description"]
        self.next_section = None
        if "next_section" in turn.attrib:
            self.next_section = int(turn.attrib["next_section"])


class Rebus:
    def __init__(self, rebus):
        self.id = rebus.attrib["id"]
        self.number = int(rebus.attrib["number"])
        self.frame_offset = int(rebus.attrib["frame_offset"])
        self.find_frame_before = 50
        if "find_frames_before" in rebus.attrib:
            self.find_frame_before = int(rebus.attrib["find_frames_before"])
        self.find_frame_after = 50
        if "find_frames_after" in rebus.attrib:
            self.find_frame_after = int(rebus.attrib["find_frames_after"])

    def is_close_to(self, frame):
        first_frame = self.frame_offset - self.find_frame_before
        last_frame = self.frame_offset + self.find_frame_after
        #print("{0} < {1} < {2} -> {3}".format(first_frame, frame, last_frame, first_frame < frame < last_frame))
        return first_frame < frame < last_frame
        #if frame >= ()
        # if self.frame_offset - self.find_frame_before <= int(frame) <= self.frame_offset + self.find_frame_after:
        #     return True
        # return False


class LatLon:
    def __init__(self, segment, prefix):
        self.lat = 0.0
        self.lon = 0.0
        if prefix+"lat" in segment.attrib:
            self.lat = float(segment.attrib[prefix+"lat"])
        if prefix+"lon" in segment.attrib:
            self.lon = float(segment.attrib[prefix+"lon"])


class Segment:
    def __init__(self, segment_xml, previous_segment, section):
        self.section = section
        self.start_latlon = LatLon(segment_xml, "start_")
        self.end_latlon = LatLon(segment_xml, "end_")
        self.speed = 0.0
        if "speed_km" in segment_xml.attrib:
            self.speed = float(segment_xml.attrib["speed_km"]) / 3.6
        if "speed" in segment_xml.attrib:
            self.speed = float(segment_xml.attrib["speed"])
        self.start_frame = int(segment_xml.attrib["start_frame"])
        self.end_frame = int(segment_xml.attrib["end_frame"])
        self.start_distance = 0.0 #TODO: take start_offset into account in some way...
        if previous_segment is not None:
            self.start_distance = previous_segment.end_distance + previous_segment.distance_per_frame
        self.end_distance = self.start_distance + ((self.end_frame - self.start_frame) / section.fps) * self.speed
        self.distance_per_frame = (self.end_distance - self.start_distance) / (self.end_frame - self.start_frame)

    def calculate_distance(self, frame_number):
        return self.start_distance + (frame_number - self.start_frame) * self.distance_per_frame

    def calculate_frame_from_distance(self, distance):
        # TODO: take start offset into account
        #dist_in_segment = distance - self.start_distance
        dist_in_segment = distance

        # frames / fps = seconds
        # distance = seconds * speed = frames * speed / fps
        # -> frames = distance * fps / speed
        return int(dist_in_segment * self.section.fps / self.speed) # TODO: take start offset into account + self.start_frame


class Section:
    def __init__(self, section, track_information):
        self.section_number = int(section.attrib["number"])
        self.movie_file = os.path.abspath(os.path.join(section.attrib["file"].replace("#LOCATION#", track_information.location)))
        self.fps = float(section.attrib["fps"])
        self.start_offset_frame = 0
        if "start_offset_frame" in section.attrib:
            self.start_offset_frame = int(section.attrib["start_offset_frame"])
        self.end_frame = None
        if "end_frame" in section.attrib:
            self.end_frame = int(section.attrib["end_frame"])
        self.turns = []
        self.rebuses = []
        self.segments = []

        for turns in section.findall("turns"):
            for turn in turns.findall("turn"):
                self.turns.append(Turn(turn))
        for rebuses in section.findall("rebuses"):
            for rebus in rebuses.findall("rebus"):
                self.rebuses.append(Rebus(rebus))
        prev_segment = None
        for segments in section.findall("segments"):
            for segment in segments.findall("segment"):
                new_segment = Segment(segment, prev_segment, self)
                self.segments.append(new_segment)
                prev_segment = new_segment

    def get_correct_turn(self):
        for turn in self.turns:
            if turn.next_section is not None:
                return turn

    def get_start_distance(self):
        return self.calculate_section_distance(self.start_offset_frame)

    def calculate_section_distance(self, frame_number):
        for segment in self.segments:
            if segment.start_frame <= frame_number <= segment.end_frame:
                return segment.calculate_distance(frame_number)

    def calculate_frame_from_distance(self, distance):
        for segment in self.segments:
            if segment.start_distance <= distance <= segment.end_distance:
                return segment.calculate_frame_from_distance(distance)
        return 0

    def calculate_video_second_from_distance(self, distance):
        return self.calculate_frame_from_distance(distance) / self.fps

    def find_nearby_rebus(self, distance):
        frame = self.calculate_frame_from_distance(distance)
        #print("Looking for rebus at frame {0} / distance {1}".format(frame, distance))
        for rebus in self.rebuses:
            #print("  {0}".format(rebus.frame_offset))
            if rebus.is_close_to(frame):
                return rebus
        return None

class TrackInformation:
    def __init__(self, config_file):
        self.sections = {}

        self.location = os.path.dirname(os.path.abspath(config_file))

        tree = ET.parse(config_file)
        root = tree.getroot()

        self.start_section = 1
        if "start_section" in root.attrib:
            self.start_section = int(root.attrib["start_section"])
        for section_xml in root.findall("section"):
            section = Section(section_xml, self)
            self.sections[section.section_number] = section

    def get_section(self, section_number):
        if section_number in self.sections:
            return self.sections[section_number]
        return None

    def get_all_section_numbers(self):
        # TODO: from config!
        return [1, 2, 3, 4, 5, 6, 7, 8]

    def get_morning_section_numbers(self):
        #TODO: from config!
        return [1, 2, 3, 4]

    def get_afternoon_section_numbers(self):
        # TODO: from config!
        return [5, 6, 7, 8]

    def get_section_titles(self):
        # TODO: from config!
        sections = {1: "Från start till R2",
                    2: "Från R2 till R3",
                    3: "Från R3 till R4",
                    4: "Från R4 till lunch",
                    5: "Från lunch till R6",
                    6: "Från R6 till R7",
                    7: "Från R7 till R8",
                    8: "Från R8 till slutet"}
        return sections

#t = TrackInformation()