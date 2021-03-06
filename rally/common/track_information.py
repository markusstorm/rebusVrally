import os
import sys
import xml.etree.ElementTree as ET


class Turn:
    TURN_MISSED = -1
    TURN_WRONG = 0
    TURN_LEFT = 1
    TURN_RIGHT = 2
    STRAIGHT_AHEAD = 3
    direction_translation_to_enum = {"missed": TURN_MISSED, "wrong": TURN_WRONG, "left": TURN_LEFT,
                             "right": TURN_RIGHT, "straight": STRAIGHT_AHEAD}
    direction_translation_to_string = {TURN_MISSED: "missed", TURN_WRONG: "wrong", TURN_LEFT: "left",
                             TURN_RIGHT: "right", STRAIGHT_AHEAD: "straight"}

    def __init__(self, turn):
        self.direction = Turn.direction_translation_to_enum[turn.attrib["direction"]]
        self.frame_offset = int(turn.attrib["frame_offset"])
        self.description = None
        if "description" in turn.attrib:
            self.description = turn.attrib["description"]
        self.next_section = None
        if "next_section" in turn.attrib:
            self.next_section = int(turn.attrib["next_section"])
        self.automatic = False
        if "automatic" in turn.attrib:
            self.automatic = Turn.xml_attribute_to_bool(turn.attrib["automatic"])
        self.already_warned = False # To stop warnings from being printed several times
        self.already_warned_checkpoint = False

    @staticmethod
    def xml_attribute_to_bool(value):
        return value.strip().casefold() == "true".casefold()


class RebusPlace:
    def __init__(self, rebus_xml):
        self.id = rebus_xml.attrib["id"]
        self.number = int(rebus_xml.attrib["rebus_config_number"])
        self.frame_offset = int(rebus_xml.attrib["frame_offset"])
        self.find_frame_before = 50
        if "find_frames_before" in rebus_xml.attrib:
            self.find_frame_before = int(rebus_xml.attrib["find_frames_before"])
        self.find_frame_after = 50
        if "find_frames_after" in rebus_xml.attrib:
            self.find_frame_after = int(rebus_xml.attrib["find_frames_after"])
        # Next section is for when the lunch or goal has been reached via a rebus control place
        self.next_section = 0
        if "next_section" in rebus_xml.attrib:
            self.next_section = int(rebus_xml.attrib["next_section"])

    def is_close_to(self, frame):
        first_frame = self.frame_offset - self.find_frame_before
        last_frame = self.frame_offset + self.find_frame_after
        return first_frame < frame < last_frame


class LatLon:
    def __init__(self, segment, prefix):
        self.lat = 0.0
        self.lon = 0.0
        if prefix + "lat" in segment.attrib:
            self.lat = float(segment.attrib[prefix + "lat"])
        if prefix + "lon" in segment.attrib:
            self.lon = float(segment.attrib[prefix + "lon"])


class Segment:
    def __init__(self, segment_xml, default_video):
        self.default_video = default_video
        self.start_latlon = LatLon(segment_xml, "start_")
        self.end_latlon = LatLon(segment_xml, "end_")
        self.speed = 0.0
        if "speed_km" in segment_xml.attrib:
            self.speed = float(segment_xml.attrib["speed_km"]) / 3.6
        if "speed" in segment_xml.attrib:
            self.speed = float(segment_xml.attrib["speed"])
        self.start_frame = int(segment_xml.attrib["start_frame"])
        self.end_frame = int(segment_xml.attrib["end_frame"])
        # Needs to be calculated when the segments have been sorted
        self.start_distance = None
        self.distance_per_frame = None
        self.end_distance = None

    def init_distances(self, previous_segment):
        # All distances are related to the "default" video (should be FRONT)
        if previous_segment is None:
            self.start_distance = 0.0
            # For the first segment, take into account that the video might have a start_offset
            self.start_frame = max(self.start_frame, self.default_video.start_offset_frame)
        else:
            # Add an extra distance_per_frame to fill the gap onto this segment
            self.start_distance = previous_segment.end_distance + previous_segment.distance_per_frame

        self.end_distance = self.start_distance + ((self.end_frame - self.start_frame) / self.default_video.fps) * self.speed
        self.distance_per_frame = (self.end_distance - self.start_distance) / (self.end_frame - self.start_frame)

    def calculate_distance(self, frame_number):
        # All distances are related to the "default" video (should be FRONT)
        return self.start_distance + (frame_number - self.start_frame) * self.distance_per_frame

    def calculate_frame_from_distance(self, distance):
        # All distances are related to the "default" video (should be FRONT)
        # distance = 0.0 equals start_offset_frame in the default video
        dist_in_segment = distance - self.start_distance

        # frames / fps = seconds
        # distance = seconds * speed = frames * speed / fps
        # -> frames = distance * fps / speed
        segment_frame = int(dist_in_segment * self.default_video.fps / self.speed)
        return self.start_frame + segment_frame

    def build_client_config_xml(self, xml_segments):
        xml_segment = ET.SubElement(xml_segments, "segment",
                                    start_lat=str(self.start_latlon.lat),
                                    start_lon=str(self.start_latlon.lon),
                                    end_lat=str(self.end_latlon.lat),
                                    end_lon=str(self.end_latlon.lon),
                                    speed_km=str(self.speed * 3.6),
                                    start_frame=str(self.start_frame),
                                    end_frame=str(self.end_frame))

    @staticmethod
    def sorter(segment):
        return segment.start_frame


class Segments:
    def __init__(self, segments_xml, default_video):
        self.default_video = default_video
        segments = []
        for segment_xml in segments_xml.findall("segment"):
            segment = Segment(segment_xml, default_video)
            segments.append(segment)

        if len(segments) == 0:
            raise ValueError("There must be at least one segment for each section!")

        self.segments = sorted(segments, key=Segment.sorter)
        self.first_segment = self.segments[0]
        self.last_segment = self.segments[-1]
        prev_segment = None
        for seg in self.segments:
            seg.init_distances(prev_segment)
            prev_segment = segment

    def calculate_default_video_distance(self, frame_number):
        if frame_number <= self.first_segment.start_frame:
            return self.first_segment.start_distance # Really should be 0
        if frame_number >= self.last_segment.end_frame:
            return self.last_segment.end_distance

        for segment in self.segments:
            # TODO: Now that segments is sorted, it should be ok to just check against the start frame
            if segment.start_frame <= frame_number <= segment.end_frame:
                return segment.calculate_distance(frame_number)
        return 0.0

    def calculate_default_video_frame_from_distance(self, distance):
        if distance < self.first_segment.start_distance:
            return self.first_segment.start_frame
        if distance > self.last_segment.end_distance:
            return self.last_segment.end_frame

        for segment in self.segments:
            if segment.start_distance <= distance <= segment.end_distance:
                return segment.calculate_frame_from_distance(distance)
        return 0

    def get_current_video_speed(self, distance):
        if distance < self.first_segment.start_distance:
            return self.first_segment.speed
        if distance > self.last_segment.end_distance:
            return self.last_segment.speed

        for segment in self.segments:
            if segment.start_distance <= distance <= segment.end_distance:
                return segment.speed
        return 0.0

    def calculate_default_video_time_from_distance(self, distance):
        frame = self.calculate_default_video_frame_from_distance(distance)
        return frame * self.default_video

    def build_client_config_xml(self, xml_section):
        xml_segments = ET.SubElement(xml_section, "segments")
        for seg in self.segments:
            seg.build_client_config_xml(xml_segments)

    # def calculate_other_video_frame_from_distance(self, distance, video):
    #     # The distance really relates to a time in any video, so calculate the time?
    #     default_video_time = self.calculate_default_video_time_from_distance(distance)
    #     hithit
    #     default_video.fps


class Video:
    LEFT = 1
    FRONT = 2
    RIGHT = 3

    direction_map_to_int = {"left": LEFT, "front": FRONT, "right": RIGHT}
    direction_map_to_str = {LEFT: "left", FRONT: "front", RIGHT: "right"}

    def __init__(self, video_xml, track_information):
        self.org_file_str = video_xml.attrib["file"]
        self.movie_file = os.path.abspath(
            os.path.join(track_information.rally_config_object.replace_locations(video_xml.attrib["file"])))
        self.direction = Video.direction_map_to_int[video_xml.attrib["view"]]
        self.fps = float(video_xml.attrib["fps"])
        self.start_offset_frame = 0
        if "start_offset_frame" in video_xml.attrib:
            self.start_offset_frame = int(video_xml.attrib["start_offset_frame"])
        self.end_frame = None
        if "end_frame" in video_xml.attrib:
            self.end_frame = int(video_xml.attrib["end_frame"])
        self.start_offset_time = self.start_offset_frame / self.fps

    def build_client_config_xml(self, xml_videos):
        xml_video = ET.SubElement(xml_videos, "video",
                                  file=self.org_file_str,
                                  fps=str(self.fps),
                                  start_offset_frame=str(self.start_offset_frame),
                                  end_frame=str(self.end_frame),
                                  view=Video.direction_map_to_str[self.direction])


class Section:
    def __init__(self, section, track_information):
        self.section_number = int(section.attrib["number"])
        self.turns = []
        self.rebus_places = []
        self.segments = None
        self.videos = {}

        for turns in section.findall("turns"):
            for turn in turns.findall("turn"):
                self.turns.append(Turn(turn))

        for rebus_places in section.findall("rebus_places"):
            for rebus_place_xml in rebus_places.findall("rebus_place"):
                self.rebus_places.append(RebusPlace(rebus_place_xml))

        for videos in section.findall("videos"):
            for video_xml in videos.findall("video"):
                video = Video(video_xml, track_information)
                self.videos[video.direction] = video
        self.default_video = self._calculate_default_video()

        for segments_xml in section.findall("segments"):
            self.segments = Segments(segments_xml, self.default_video)

        self.default_end_distance = self.calculate_default_video_distance_from_frame(self.default_video.end_frame)

    def get_correct_turn(self):
        for turn in self.turns:
            if turn.next_section is not None and turn.next_section > 0 and turn.direction != Turn.TURN_WRONG and turn.direction != Turn.TURN_MISSED:
                return turn

    def get_closest_turn(self, frame):
        best_match = None
        best_diff = sys.maxsize
        for turn in self.turns:
            diff = abs(turn.frame_offset - frame)
            if diff < best_diff:
                best_diff = diff
                best_match = turn
        return best_match

    def get_last_turn(self):
        highest_frame = 0
        latest_turn = None
        for turn in self.turns:
            if turn.frame_offset > highest_frame:
                highest_frame = turn.frame_offset
                latest_turn = turn
        return latest_turn

    def missed_all_turns(self, distance):
        """ Returns True if the driver has passed the last turn and it is a "MISSED" turn. """
        last_turn = self.get_last_turn()
        if last_turn is not None:
            if last_turn.direction == Turn.TURN_MISSED:
                last_turn_distance = self.calculate_default_video_distance_from_frame(last_turn.frame_offset)
                if distance >= last_turn_distance:
                    return True
        return False

    def get_start_distance(self):
        # All sections start at distance 0.0 (which is the same as start_offset_frame)
        return 0.0

    def get_default_end_distance(self):
        """ Return the end distance (in the scope of the default video).
         Should be the same for all videos, but they might be configured not exactly the same. """
        return self.default_end_distance

    def calculate_default_video_distance_from_frame(self, frame_number):
        return self.segments.calculate_default_video_distance(frame_number)

    def calculate_default_video_frame_from_distance(self, distance):
        return self.segments.calculate_default_video_frame_from_distance(distance)

    def calculate_other_video_frame_from_distance(self, distance, viewing_direction):
        video = self.get_video(viewing_direction)
        if video is not None:
            # Calculate the default video frame
            video_frame = self.calculate_default_video_frame_from_distance(distance)
            # The number of frames into the section (i.e. with regard to the offset frames)
            frame_in_section = video_frame - self.default_video.start_offset_frame
            time_in_section = frame_in_section / self.default_video.fps

            # Ok, so a distance corresponds to a number of seconds into the section
            # Now make a similar calculation for the other video.
            # Start with calculating the number of frames that the time corresponds to in this video
            frame_count = time_in_section * video.fps
            # Then simply add the start offset time (already calculated)
            return frame_count + video.start_offset_frame
        return 0

    def calculate_default_video_second_from_distance(self, distance):
        # All frames and times in video relates to the start of the actual video, NOT the start_offset
        default_video_frame = self.segments.calculate_default_video_frame_from_distance(distance)
        return default_video_frame / self.default_video.fps

    def get_current_video_speed(self, distance):
        return self.segments.get_current_video_speed(distance)

    def calculate_other_video_second_from_distance(self, distance, viewing_direction):
        video = self.get_video(viewing_direction)
        if video is not None:
            # Calculate the default video frame
            video_frame = self.calculate_default_video_frame_from_distance(distance)
            # The number of frames into the section (i.e. with regard to the offset frames)
            frame_in_section = video_frame - self.default_video.start_offset_frame
            time_in_section = frame_in_section / self.default_video.fps

            # Ok, so we have the time into the section, then simply return that + the start offset time.
            return time_in_section + video.start_offset_time

    def find_nearby_rebus_place(self, distance):
        frame = self.calculate_default_video_frame_from_distance(distance)
        # print("Looking for rebus at frame {0} / distance {1}".format(frame, distance))
        for rebus_place in self.rebus_places:
            # print("  {0}".format(rebus.frame_offset))
            if rebus_place.is_close_to(frame):
                return rebus_place
        return None

    def build_client_config_xml(self, rally_sections):
        xml_section = ET.SubElement(rally_sections, "section",
                                    number=str(self.section_number))
        xml_videos = ET.SubElement(xml_section, "videos")
        for video in self.videos.values():
            video.build_client_config_xml(xml_videos)
        xml_turns = ET.SubElement(xml_section, "turns")
        self.segments.build_client_config_xml(xml_section)

    def get_default_video(self):
        return self.default_video

    def get_video(self, direction):
        if direction in self.videos:
            return self.videos[direction]
        return None

    def _calculate_default_video(self):
        """ Return the front view, this is the default view to calculate distances from.
            If there is no front view, then return the first video encountered.
        """
        if Video.FRONT in self.videos:
            return self.videos[Video.FRONT]
        for video in self.videos.values():
            return video
        return None


class TrackInformation:
    def __init__(self, rally_config_object, config_file=None, xml=None):
        self.sections = {}
        self.rally_config_object = rally_config_object
        try:
            if config_file is not None:
                tree = ET.parse(config_file)
                xml = tree.getroot()

            self.start_section = 1
            if "start_section" in xml.attrib:
                self.start_section = int(xml.attrib["start_section"])
            for section_xml in xml.findall("section"):
                section = Section(section_xml, self)
                self.sections[section.section_number] = section
        except FileNotFoundError as e:
            raise ValueError("ERROR! Sections configuration file {0} not found! {1}".format(config_file, e))
        except ET.ParseError as e:
            raise ValueError("ERROR! Error when reading sections configuration {0}: {1}".format(config_file, e))

    def get_section(self, section_number):
        if section_number in self.sections:
            return self.sections[section_number]
        return None

    def get_all_section_numbers(self):
        # TODO: from config!
        return [1, 2, 3, 4, 5, 6, 7, 8]

    def get_morning_section_numbers(self):
        # TODO: from config!
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

    def build_client_config_xml(self, root):
        rally_sections = ET.SubElement(root, "sections", start_section=str(self.start_section))
        for section in self.sections.values():
            section.build_client_config_xml(rally_sections)

# t = TrackInformation()
