from threading import Lock

import cv2


class MyVideoCapture:
    def __init__(self, track_information, view_direction):
        self.frame_number = 0
        self.frame_time = 0.0
        self.vid = None
        self.width = 0
        self.height = 0
        self.fps = 0
        self.mutex = Lock()
        self.track_information = track_information
        self.view_direction = view_direction
        self.latest_image = None

    def change_section(self, new_section, distance_in_new_section):
        #print("1.0")
        with self.mutex:
            #print("1.1")
            if self.vid is not None:
                if self.vid.isOpened():
                    self.vid.release()

            #print("1.2")
            section = self.track_information.get_section(new_section)
            video_obj = section.get_video(self.view_direction)
            if video_obj is None:
                return
            video_file = video_obj.movie_file

            self.latest_image = None

            # Open the video source
            print("Changing video to: {}".format(video_file))
            self.vid = cv2.VideoCapture(video_file)
            #print("1.3")
            if not self.vid.isOpened():
                raise ValueError("Unable to open video source")

            # Get video source width and height
            self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
            self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
            self.fps = self.vid.get(cv2.CAP_PROP_FPS)
            #print("{0}x{1} at {2} fps".format(self.width, self.height, self.fps))
            #print(self.vid.get(cv2.CAP_PROP_FPS))
            #print(self.vid.get(cv2.CAP_PROP_FRAME_COUNT))
            #print(self.vid.get(cv2.CAP_PROP_POS_FRAMES))
            #print(self.vid.get(cv2.CAP_PROP_POS_MSEC))
            self.frame_number = 0
            self.frame_time = 0.0

            if distance_in_new_section > 0:
                #print("1.4")
                offset_sec = section.calculate_other_video_second_from_distance(distance_in_new_section, self.view_direction)
                offset_ms = offset_sec * 1000
                #print("Start offset: {0}".format(offset_ms))
                self._seek_ms(offset_ms)
                #print("Back from seek")
                self.frame_time = offset_ms
                self.frame_number = section.calculate_other_video_frame_from_distance(distance_in_new_section, self.view_direction)

    # Mutex protected
    def seek_ms(self, ms):
        #print("2.0")
        with self.mutex:
            #print("2.1")
            self._seek_ms(ms)
            #print("2.2")

    # NOT mutex protected
    def _seek_ms(self, ms):
        #print("3")
        self.latest_image = None
        self.vid.set(cv2.CAP_PROP_POS_MSEC, ms)

    def get_frame(self, catch_new=True):
        #print("get_frame({0})".format(catch_new))
        #print("4.0")
        if not catch_new:
            if self.latest_image is not None:
                return True, self.latest_image

        with self.mutex:
            #print("4.1")
            if self.vid is None:
                return False, None
            #print("4.2")
            if self.vid.isOpened():
                #print("4.3")
                #print(self.vid.get(cv2.CAP_PROP_POS_FRAMES))
                #print(self.vid.get(cv2.CAP_PROP_POS_MSEC))
                ret, frame = self.vid.read()
                #print("4.4")
                self.frame_time = self.vid.get(cv2.CAP_PROP_POS_MSEC)
                self.frame_number = self.vid.get(cv2.CAP_PROP_POS_FRAMES)
                if ret:
                    #print("4.5")
                    # Return a boolean success flag and the current frame converted to BGR
                    self.latest_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    return ret, self.latest_image
                else:
                    #print("4.6")
                    # TODO: what does it mean that we return the latest image here?
                    return ret, self.latest_image
            else:
                #print("4.7")
                return False, None

    # Release the video source when the object is destroyed
    def __del__(self):
        if self.vid is not None:
            if self.vid.isOpened():
                self.vid.release()
