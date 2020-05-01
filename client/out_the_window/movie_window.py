import datetime
import tkinter
from functools import partial
from threading import Lock

import cv2
import PIL.Image, PIL.ImageTk
import time
import argparse

from client.common.client_config import ClientRallyConfig
from client.out_the_window.video_capture import MyVideoCapture
from rally.common.subclient_communicator import SubClientCommunicator

#https://stackoverflow.com/questions/56534609/hardware-accelerated-decoding-with-opencv-and-python-on-windows-msmt-intelmfx
from rally.common.track_information import Video

direction_translator = {"front": "framåt", "left": "till vänster", "right": "till höger"}

parser = argparse.ArgumentParser(description='The steering GUI')
parser.add_argument("-p", "--port", type=int, help="UDP port of the main client", required=True)
parser.add_argument("-c", "--client_index", type=int, help="Client index, used in communication", required=True)
parser.add_argument("-u", "--user_id", type=int, help="User ID", required=True)
parser.add_argument("-r", "--rally_configuration", type=str, help="Path to the rally configuration to use", required=True)
parser.add_argument("-d", "--data_path", type=str, help="Path to root of where rally data is stored", required=True)
parser.add_argument("-v", "--view_direction", type=str, help="View direction (left, front, right)", required=True)
parser.add_argument("-m", "--disallow_moving_direction", action="append", help="Disallow video to be shown for specified view (left, front, right) when the bus is moving", required=False)
parser.add_argument("-s", "--disallow_stopped_direction", action="append", help="Disallow video to be shown for specified view (left, front, right) when the bus is stopped", required=False)
args = parser.parse_args()
#print(args)


def remove_from_list(input, disallow):
    if disallow is None:
        return input
    for val in disallow:
        direction = val.casefold()
        if direction in Video.direction_map_to_int:
            input[Video.direction_map_to_int[direction]] = False
    return input


allowed_when_stopped = remove_from_list({Video.LEFT: True, Video.FRONT: True, Video.RIGHT: True}, args.disallow_stopped_direction)
allowed_when_moving = remove_from_list({Video.LEFT: True, Video.FRONT: True, Video.RIGHT: True}, args.disallow_moving_direction)


#Blur: https://www.geeksforgeeks.org/opencv-motion-blur-in-python/

class App:
    def __init__(self, window, direction_str, track_information):
        self.debug = False
        self.terminate = False
        self.track_information = track_information
        window_title = "Utsikt {0}".format(direction_translator[direction_str])
        self.main_direction = Video.direction_map_to_int[direction_str]
        self.viewing_direction = self.main_direction
        print("Main direction is: {0}".format(Video.direction_map_to_str[self.main_direction]))
        self.force_update = False
        self.connected = False
        self.reconfiguring = False
        self.speed = 0.0
        self.stopped = True
        self.distance = 0.0
        self.current_section = track_information.start_section
        self.pos_time = None
        self.delay = int(1.0/30.0) # Mostly we are dealing with 30fps video, so set a default delay based on that
        self.last_frame_time_shown = -1

        self.buttons = {}
        self.button_states = {Video.LEFT: False, Video.FRONT: False, Video.RIGHT: False}

        self.sub_client_communicator = SubClientCommunicator(args, pos_receiver=self.on_pos_updates)
        self.sub_client_communicator.start()

        # open video source (by default this will try to open the computer webcam)
        self.view_video_caps = {Video.LEFT: None, Video.FRONT: None, Video.RIGHT: None}
        self.view_video_caps[self.viewing_direction] = MyVideoCapture(self.track_information, self.viewing_direction)

        self.window = window
        self.window.title(window_title)
        self.canvas = None

        self.update()

        if self.debug:
            self.frame_label = None

        self.window.mainloop()
        self.terminate = True

    def current_video_cap(self):
        # TODO: make sure there is an object here!
        return self.view_video_caps[self.viewing_direction]

    def change_video(self):
        self.reconfiguring = True

        # Forget about the videos that aren't shown
        vid_cap = self.current_video_cap()
        self.view_video_caps = {Video.LEFT: None, Video.FRONT: None, Video.RIGHT: None}
        self.view_video_caps[self.viewing_direction] = vid_cap

        vid_cap.change_section(self.current_section, self.distance)
        self.force_update = True
        if self.canvas is None:
            # Create a canvas that can fit the above video source size
            self.canvas = tkinter.Canvas(self.window, width=vid_cap.width, height=vid_cap.height)
            self.canvas.grid(row=0, column=0, columnspan=3, sticky=tkinter.W)

            self.buttons[Video.LEFT] = tkinter.Button(self.window, text="Titta åt vänster")
            self.buttons[Video.LEFT].bind("<ButtonPress-1>", partial(self.video_button_on, Video.LEFT))
            self.buttons[Video.LEFT].bind("<ButtonRelease-1>", partial(self.video_button_off, Video.LEFT))
            self.buttons[Video.LEFT].bind("<Leave>", partial(self.video_button_off, Video.LEFT))
            self.buttons[Video.LEFT].grid(row=1, column=0, sticky=tkinter.W)

            self.buttons[Video.FRONT] = tkinter.Button(self.window, text="Titta framåt")
            self.buttons[Video.FRONT].bind("<ButtonPress-1>", partial(self.video_button_on, Video.FRONT))
            self.buttons[Video.FRONT].bind("<ButtonRelease-1>", partial(self.video_button_off, Video.FRONT))
            self.buttons[Video.FRONT].bind("<Leave>", partial(self.video_button_off, Video.FRONT))
            self.buttons[Video.FRONT].grid(row=1, column=1)

            self.buttons[Video.RIGHT] = tkinter.Button(self.window, text="Titta åt höger")
            self.buttons[Video.RIGHT].bind("<ButtonPress-1>", partial(self.video_button_on, Video.RIGHT))
            self.buttons[Video.RIGHT].bind("<ButtonRelease-1>", partial(self.video_button_off, Video.RIGHT))
            self.buttons[Video.RIGHT].bind("<Leave>", partial(self.video_button_off, Video.RIGHT))
            self.buttons[Video.RIGHT].grid(row=1, column=2, sticky=tkinter.E)

            self.update_view_buttons()

            if self.debug:
                self.frame_label = tkinter.Label(self.window, text="FRAME COUNT")
                self.frame_label.place(x=0, y=0)

        self.reconfiguring = False

    def video_button_on(self, direction, event):
        self.button_states[direction] = True
        self.update_view()

    def video_button_off(self, direction, event):
        self.button_states[direction] = False
        self.update_view()

    def update_view(self):
        direction = self.main_direction
        # Choose the first pressed button to override the default view direction, there really should only be one pressed button...
        for key in self.button_states:
            if self.button_states[key]:
                direction = key
                break

        if self.viewing_direction != direction:
            self.viewing_direction = direction
            if self.view_video_caps[direction] is None:
                self.view_video_caps[direction] = MyVideoCapture(self.track_information, self.viewing_direction)
                self.view_video_caps[direction].change_section(self.current_section, self.distance)
            self.force_update = True

    def update_view_buttons(self):
        if self.terminate:
            return
        global allowed_when_stopped, allowed_when_moving
        section = self.track_information.get_section(self.current_section)
        for direction in self.buttons:
            state = "normal"
            if self.stopped:
                if not allowed_when_stopped[direction]:
                    state = "disabled"
            else:
                if not allowed_when_moving[direction]:
                    state = "disabled"
            if section.get_video(direction) is None:
                state = "disabled"
            self.buttons[direction].config(state=state)

    def on_pos_updates(self, status_information):
        self.pos_time = datetime.datetime.now()
        self.speed = status_information.speed
        self.stopped = status_information.stopped
        self.distance = status_information.distance
        if status_information.force_update:
            self.force_update = True
        if not self.connected:
            self.current_section = status_information.current_section
            self.change_video()
            self.connected = True
            self.force_update = True
        else:
            if self.current_section != status_information.current_section:
                self.current_section = status_information.current_section
                self.change_video()
        self.update_view_buttons()

    def seek(self, vid_cap, video_target_msecs, video_speed):
        # TODO: calculate how far into the future we should seek based on average seek time
        seek_time_ms = 1000
        # How many frame would be shown in one realtime second with the current speed?
        seek_extra_frames = vid_cap.fps * self.speed / video_speed
        # How much time does that correspond to in the video?
        seek_extra_ms = seek_extra_frames / vid_cap.fps
        vid_cap.seek_ms(video_target_msecs + seek_extra_ms)

    def update(self):
        delay = self._update()
        if delay is None or not delay:
            self.window.after(self.delay, self.update)
        else:
            self.window.after(delay, self.update)

    def _update(self):
        # wait for position data to start arriving
        if not self.connected or self.pos_time is None:
            return False
        # Changing video, so don't show anything
        if self.reconfiguring:
            return False

        vid_cap = self.current_video_cap()

        if self.force_update:
            self.last_frame_time_shown = -1

        now = datetime.datetime.now()
        diff = now - self.pos_time
        interpolated_distance = self.distance + self.speed * diff.total_seconds()
        section = self.track_information.get_section(self.current_section)
        video_speed = 50.0/3.6
        if section is not None:
            video_speed = section.get_current_video_speed(interpolated_distance)
            if interpolated_distance < section.get_start_distance():
                interpolated_distance = section.get_start_distance()
        video_target_secs = self.track_information.get_section(self.current_section).calculate_other_video_second_from_distance(interpolated_distance, self.viewing_direction)
        video_target_msecs = video_target_secs * 1000

        wait = 1
        if self.speed < 0.0:
            # We are backing, no fancy methods to handle this, simply seek always when we need a new frame
            if abs(video_target_msecs - self.last_frame_time_shown) < vid_cap.one_frame_ms:
                # We are still close to what we last displayed
                ret, frame, frame_time = vid_cap.get_frame(self.force_update)
                wait = vid_cap.one_frame_ms
            else:
                # We are backing and need a new frame, so seek and force the next frame
                vid_cap.seek_ms(video_target_msecs)
                ret, frame, frame_time = vid_cap.get_frame(True)
                wait = 1 # Draw as quickly as possible
        else:
            # Either standing still or moving forward
            if abs(video_target_msecs - self.last_frame_time_shown) < vid_cap.one_frame_ms:
                # We are still close to what we last displayed
                ret, frame, frame_time = vid_cap.get_frame(self.force_update)
                wait = vid_cap.one_frame_ms
            else:
                # We need to show a new frame
                diff_ms = video_target_msecs - self.last_frame_time_shown
                if diff_ms > 0.0:
                    behind = diff_ms
                    # We are behind what we should show
                    if behind > 1000:
                        # We are more than one second behind than what should be shown
                        # Seek to a time that is a bit into the future
                        self.seek(vid_cap, video_target_msecs, video_speed)
                        ret, frame, frame_time = vid_cap.get_frame(True)
                        wait = 1 # Not sure, but should probably try do display again as soon as possible, to find out where we stand
                    else:
                        # Hope that we can catch up with the video soon
                        ret, frame, frame_time = vid_cap.get_frame(True)
                        wait = 1 # We are behind, so don't wait around to show the next frame
                elif diff_ms < 0.0:
                    # We are ahead of what we should show
                    ahead_ms = -diff_ms

                    # How long would it take for the bus to arrive at the same time with the current speed?
                    if abs(self.speed) > 0.01:
                        travel_length = video_speed * ahead_ms / 1000
                        t = travel_length / self.speed
                        t_ms = t * 1000
                    else:
                        t_ms = 10000
                    if t_ms > 3000:
                        # It would take more than three wall clock seconds for the bus to catch up with the
                        # video, so seek and force a frame update
                        self.seek(vid_cap, video_target_msecs, video_speed)
                        ret, frame, frame_time = vid_cap.get_frame(True)
                        wait = 1
                    else:
                        # In not too long we could possibly catch up with the video
                        # TODO: should probably return a new frame here every now and then, to not make the video too jumpy
                        ret, frame, frame_time = vid_cap.get_frame(False)
                        wait = vid_cap.one_frame_ms

        self.force_update = False
        self.last_frame_time_shown = frame_time

        if ret:
            self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
            self.canvas.create_image(0, 0, image=self.photo, anchor=tkinter.NW)
        if self.debug:
            self.frame_label["text"] = str(vid_cap.frame_number)

        return min(int(wait), 100)

#https://www.opencv-srf.com/2017/12/play-video-file-backwards.html - mini-buffrad approach
#https://stackoverflow.com/questions/11260042/reverse-video-playback-in-opencv
#(https://www.life2coding.com/play-a-video-in-reverse-mode-using-python-opencv/)


rally_configuration = ClientRallyConfig(args.rally_configuration, args.data_path)

# Create a window and pass it to the Application object
App(tkinter.Tk(), args.view_direction, rally_configuration.track_information)