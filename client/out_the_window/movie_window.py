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
        self.delay = 15 #TODO: set based on FPS
        self.drop_a_frame = False
        self.first_display = True
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

        # Debug, TODO: remove
        self.frame_label = None

        #print("A")

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

            # TODO: remove frame counter or make configurable
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
            #print("Force update")

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
        #print("pos")
        self.pos_time = datetime.datetime.now()
        self.speed = status_information.speed
        self.stopped = status_information.stopped
        self.distance = status_information.distance
        if status_information.force_update:
            self.force_update = True
        #print(self.current_section, status_information.current_section)
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

    def update(self):
        delay = self._update()
        if delay is None or not delay:
            self.window.after(self.delay, self.update)
        else:
            self.window.after(delay, self.update)

    def _update(self):
        if not self.connected:
            #print("Not connected")
            return False
        if self.reconfiguring:
            #print("Reconfiguring")
            return False

        vid_cap = self.current_video_cap()

        if self.first_display:
            #print("First display")
            self.first_display = False
            ret, frame = vid_cap.get_frame()
            if ret:
                self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
                self.canvas.create_image(0, 0, image=self.photo, anchor=tkinter.NW)
            return False

        # wait for position data to start arriving
        if self.pos_time is None:
            #print("No position")
            return False
        if self.speed == 0.0 and not self.force_update:
            #print("Speed is 0")
            return False

        now = datetime.datetime.now()
        diff = now - self.pos_time
        interpolated_distance = self.distance + self.speed * diff.total_seconds()
        section = self.track_information.get_section(self.current_section)
        if section is not None:
            if interpolated_distance < section.get_start_distance():
                interpolated_distance = section.get_start_distance()
        #print("id {0}".format(interpolated_distance))
        #print("dist: {0}".format(interpolated_distance))
        # 50 km/h statisk hastighet -> 50/3.6 m/s
        #video_speed = 50.0 / 3.6
        # With that speed, the current distance corresponds to
        #video_target_secs = interpolated_distance / video_speed
        video_target_secs = self.track_information.get_section(self.current_section).calculate_other_video_second_from_distance(interpolated_distance, self.viewing_direction)

        # Before we try to show a frame, see if we should wait more or backup
        # TODO: remove a lot of duplicated code (but first get something to work at all...)
        diff_ms = vid_cap.frame_time - video_target_secs * 1000.0
        if diff_ms > 0.0:
            # Ok, so video is ahead of time
            ret = False
            if self.speed < -0.01:
                # We are backing, should seek in the video and then show one frame
                vid_cap.seek_ms(video_target_secs * 1000)
                ret, frame = vid_cap.get_frame(True)
                self.force_update = False
            elif self.force_update:
                # Video is ahead of time and we have a forced update, then also seek
                vid_cap.seek_ms(video_target_secs * 1000)
                ret, frame = vid_cap.get_frame(False)
                self.force_update = False
            if ret:
                self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
                self.canvas.create_image(0, 0, image=self.photo, anchor=tkinter.NW)
                self.frame_label["text"] = str(vid_cap.frame_number)
                return self.delay
            # We are ahead with the video, wait for some more time before showing the next frame
            return min(int(diff_ms), 100)

        # Get a frame from the video source
        # if self.drop_a_frame:
        #     self.drop_a_frame = False
        #     self.vid.get_frame()
        #ret, frame = vid_cap.get_frame(not self.force_update)

        ret, frame = vid_cap.get_frame(diff_ms < self.delay or self.force_update)
        self.force_update = False
        # if self.viewing_direction != self.main_direction:
        #     print(self.viewing_direction)
        # print(ret)

        if ret:
            self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(frame))
            self.canvas.create_image(0, 0, image = self.photo, anchor = tkinter.NW)

        self.frame_label["text"] = str(vid_cap.frame_number)

        # OK, this have to get better in some way... but it's a first try
        # Now we have presented a frame, it has the time self.vid.frame_time (millisecs)
        diff_ms = vid_cap.frame_time - video_target_secs*1000.0
        #print("Diff: {0}".format(diff_ms))
        # if diff_ms is > 0 then we have presented the frame too early, so we need to wait
        # otherwise we should just present the next frame as soon as possible
        wait = 1
        if diff_ms > 0.0:
            wait = diff_ms
        else:
            if diff_ms < -2000:
                # Too far behind, try to seek in the video
                vid_cap.seek_ms(video_target_secs*1000 + 1000) #Add a bit of extra time, since it will take time to seek
            elif diff_ms < -500:
                self.drop_a_frame = True

        #print("vid {0} and target {1} -> wait {2}".format(self.vid.frame_time, video_target_secs*1000.0, wait))
        #self.window.after(int(wait), self.update)
        return min(int(wait), 100)

#https://www.opencv-srf.com/2017/12/play-video-file-backwards.html - mini-buffrad approach
#https://stackoverflow.com/questions/11260042/reverse-video-playback-in-opencv
#(https://www.life2coding.com/play-a-video-in-reverse-mode-using-python-opencv/)


rally_configuration = ClientRallyConfig(args.rally_configuration, args.data_path)

# Create a window and pass it to the Application object
App(tkinter.Tk(), args.view_direction, rally_configuration.track_information)