import argparse
import datetime
from tkinter import *
from tkinter import messagebox

from PIL import ImageTk, Image

from client.common.client_config import ClientRallyConfig
from rally.common.subclient_communicator import SubClientCommunicator
from rally.protocol import clientprotocol_pb2


class SteeringWindow:
    NONE = 0
    LEFT = 1
    RIGHT = 2

    def __init__(self, client_index, track_information):
        self.my_client_index = client_index
        self.connected = False
        self.speed = 0.0
        self.distance = 0.0
        self.accumulated_movement = 0.0
        self.track_information = track_information
        self.current_section = track_information.start_section
        self.looking_for_rebus = False
        self.prev_sample = None
        self.rally_is_started = False
        self.current_gas = 0.0
        self.current_brake = 0.0
        self.backup_timeout = None
        self.backing = False
        self.stopped = True
        self.indicator_light = SteeringWindow.NONE
        self.showing_message = False

        self.window = None
        self.speed_variable = None
        self.looking_for_rebus_label = None
        self.backing_label = None
        self.speed_indicator_image = None
        self.speed_indicator_label = None
        self.turn_indicator_images = {}
        self.turn_indicator_labels = {}
        self.pedals_image = None
        self.pedals_label = None
        self.backup_image = None
        self.backup_label = None
        self.f_indicators = None
        self.speed_label = None

        self.layout()

        self.sub_client_communicator = SubClientCommunicator(args, pos_receiver=self.on_pos_update)
        self.sub_client_communicator.start()

    def layout(self):
        self.window = Tk()
        self.window.title("Dedicated driver")

        # w = self.image1.width()
        # h = self.image1.height()
        # self.window.geometry('%dx%d+0+0' % (w, h))
        # background_label = Label(self.window, image=self.image1)
        # background_label.place(x=0, y=0, relwidth=1, relheight=1)

        messages_text = Text(self.window, height=5, width=60)
        messages_text.insert(END,
                             "Klicka (och håll) på gas/broms för att köra bussen. Ju högre upp på pedalen, "
                             "desto kraftigare gas/broms.\n"
                             "Klicka på riktningsindikatorerna för att förbereda sväng.\n"
                             "Stanna och klicka på backa-knapparna för att backa."
                             )
        messages_text.config(state=DISABLED)
        messages_text.grid(row=0, column=0)

        self.f_indicators = Frame(self.window)

        self.speed_indicator_image = ImageTk.PhotoImage(Image.open('speed_frame.png'))
        # TODO: frame around the value?
        self.speed_label = Label(self.f_indicators, text="0", font=("Arial Bold", 50), width=3)
        self.speed_variable = StringVar()
        self.speed_label["textvariable"] = self.speed_variable

        self.turn_indicator_images[SteeringWindow.LEFT] = \
            {True: ImageTk.PhotoImage(Image.open('blinkers_left_on_70.png')),
             False: ImageTk.PhotoImage(Image.open('blinkers_left_off_70.png'))}
        self.turn_indicator_images[SteeringWindow.RIGHT] = \
            {True: ImageTk.PhotoImage(Image.open('blinkers_right_on_70.png')),
             False: ImageTk.PhotoImage(Image.open('blinkers_right_off_70.png'))}

        lbl = Label(self.f_indicators, image=self.turn_indicator_images[SteeringWindow.LEFT][False], text="11")
        lbl.bind("<Button-1>", self.left_indicator_clicket)
        lbl.grid(row=0, column=0)
        self.turn_indicator_labels[SteeringWindow.LEFT] = lbl
        self.speed_label.grid(row=0, column=1)
        lbl = Label(self.f_indicators, image=self.turn_indicator_images[SteeringWindow.RIGHT][False])
        lbl.bind("<Button-1>", self.right_indicator_clicket)
        lbl.grid(row=0, column=2)
        self.turn_indicator_labels[SteeringWindow.RIGHT] = lbl

        self.f_indicators.grid(row=1, column=0)

        self.pedals_image = ImageTk.PhotoImage(Image.open('gas_and_brake.png'))
        self.pedals_label = Label(self.window, image=self.pedals_image)
        self.pedals_label.grid(row=2, column=0)
        # https://effbot.org/tkinterbook/tkinter-events-and-bindings.htm
        self.pedals_label.bind("<Button-1>", self.mouse_event)
        self.pedals_label.bind("<B1-Motion>", self.mouse_event)
        self.pedals_label.bind("<ButtonRelease-1>", self.release_mouse)

        self.backup_image = ImageTk.PhotoImage(Image.open('backup.png'))
        self.backup_label = Label(self.window, image=self.backup_image)
        self.backup_label.grid(row=3, column=0)
        self.backup_label.bind("<Button-1>", self.backup_clicked)

        self.looking_for_rebus_label = Label(self.window, text="Letar efter rebus!", font=("Arial Bold", 30), background="blue")
        self.backing_label = Label(self.window, text="Backar...", font=("Arial Bold", 30), background="blue")

    def run(self):
        self.window.after(1, self.update_speed)
        self.window.after(100, self.send_to_client)
        self.window.mainloop()
        self.sub_client_communicator.stop()

    def on_pos_update(self, status_information):
        #print(self.speed, status_information.speed, self.distance, status_information.distance)
        if self.backing:
            self.backing_label.place(x=140, y=250)
        else:
            if self.backing_label is not None:
                self.backing_label.place_forget()

        self.stopped = status_information.stopped or status_information.looking_for_rebus
        #if self.stopped:
        self.distance = status_information.distance
        if status_information.looking_for_rebus != self.looking_for_rebus:
            self.looking_for_rebus = status_information.looking_for_rebus
            if self.looking_for_rebus:
                self.looking_for_rebus_label.place(x=80, y=250)
            else:
                if self.looking_for_rebus_label is not None:
                    self.looking_for_rebus_label.place_forget()

        self.rally_is_started = status_information.rally_is_started
        if not self.connected:
            self.current_section = status_information.current_section
            self.connected = True
        else:
            if self.current_section != status_information.current_section:
                # New section!
                self.accumulated_movement = 0.0
                self.indicator_light = SteeringWindow.NONE
                self.current_section = status_information.current_section
                self.update_turn_indicators()

    def send_to_client(self):
        if not self.connected:
            self.window.after(1000, self.send_to_client)
            return
        client_to_server = clientprotocol_pb2.ClientToServer()
        client_to_server.counter = self.my_client_index
        client_to_server.pos_update.SetInParent()
        client_to_server.pos_update.speed = self.speed
        client_to_server.pos_update.delta_distance = self.accumulated_movement
        self.accumulated_movement = 0.0
        client_to_server.pos_update.current_section = self.current_section
        client_to_server.pos_update.indicator = self.indicator_light
        self.sub_client_communicator.send(client_to_server)
        self.window.after(1000, self.send_to_client)

    def brake_pedal(self, event, button):
        if button:
            #percent = (1.0 - (event.y - 535) / (790 - 535))
            percent = (1.0 - (event.y - 38) / (155 - 38))
        else:
            percent = 0
        self.current_brake = percent

    def gas_pedal(self, event, button):
        if button:
            if self.rally_is_started:
                #percent = (1.0 - (event.y - 535) / (790 - 535))
                percent = (1.0 - event.y / 161)
            else:
                percent = 0
                self.show_drive_error()
        else:
            percent = 0
        self.current_gas = percent

    def show_drive_error(self):
        if self.showing_message:
            return
        self.window.lower()
        self.showing_message = True
        messagebox.showerror("Kan inte köra",
                             "Antingen har rallyt inte startat än eller så måste du bara vänta in första positionsuppdateringen från servern, det tar upp till 10 sekunder",
                             parent=self.window)
        self.showing_message = False

    def mouse_event(self, event):
        #print(event.x, event.y)
        if 64 <= event.x <= 178 and 38 <= event.y <= 155:
            self.brake_pedal(event, True)
            self.gas_pedal(event, False)
        elif 277 <= event.x <= 379 and 0 <= event.y <= 161:
            self.gas_pedal(event, True)
            self.brake_pedal(event, False)
        else:
            self.brake_pedal(event, False)
            self.gas_pedal(event, False)

    def left_indicator_clicket(self, event):
        self.indicator_clicked(SteeringWindow.LEFT)

    def right_indicator_clicket(self, event):
        self.indicator_clicked(SteeringWindow.RIGHT)

    def indicator_clicked(self, which):
        if self.indicator_light == which:
            self.indicator_light = SteeringWindow.NONE
        else:
            self.indicator_light = which
        self.update_turn_indicators()

    def update_turn_indicators(self):
        print("Turn indicator: {0}".format(self.indicator_light))
        self.turn_indicator_labels[SteeringWindow.LEFT]["image"] = \
            self.turn_indicator_images[SteeringWindow.LEFT][self.indicator_light == SteeringWindow.LEFT]
        self.turn_indicator_labels[SteeringWindow.RIGHT]["image"] = \
            self.turn_indicator_images[SteeringWindow.RIGHT][self.indicator_light == SteeringWindow.RIGHT]


    def backup_clicked(self, event):
        #print(event.x, event.y)
        if 5 <= event.x <= 85 and 90 <= event.y <= 150:
            self.backup(10)
        if 115 <= event.x <= 200 and 64 <= event.y <= 150:
            self.backup(50)
        if 225 <= event.x <= 310 and 30 <= event.y <= 150:
            self.backup(100)
        if 340 <= event.x <= 420 and 5 <= event.y <= 150:
            self.backup(300)

    def backup(self, amount):
        if not self.rally_is_started:
            self.show_drive_error()
            return

        now = datetime.datetime.now()
        if self.backup_timeout is not None:
            if now < self.backup_timeout:
                print("Unable to back more just yet, still waiting for the latest command to finish")
                return
        if not self.stopped:
            if self.showing_message:
                return
            self.window.lower()
            self.showing_message = True
            messagebox.showerror("Kan inte backa",
                                 "Du måste stå stilla innan du kan backa.",
                                 parent=self.window)
            self.showing_message = False
            return

        self.backing = True
        self.speed = -50/3.6
        secs_per_meter = 3.6/50
        secs = secs_per_meter * amount
        #print("Wait for {0} seconds".format(secs))
        self.backup_timeout = now + datetime.timedelta(seconds=secs)

    def release_mouse(self, event):
        self.brake_pedal(event, False)
        self.gas_pedal(event, False)

    def update_speed(self):
        if self.looking_for_rebus or not self.connected:
            self.window.after(100, self.update_speed)
            return

        now = datetime.datetime.now()
        if self.prev_sample is not None:
            diff = now - self.prev_sample
            secs = diff.total_seconds()
            self.accumulated_movement += self.speed * secs

            # if self.distance < 0.0:
            #     self.distance = 0.0
            # if section is not None:
            #     if self.distance < section.get_start_distance():
            #         self.distance = section.get_start_distance()
            #         if self.backing:
            #             self.backing = False
            #             self.speed = 0
            #             self.backup_timeout = None
        self.prev_sample = now

        interpolated_distance = self.distance + self.accumulated_movement
        if interpolated_distance < 0.0:
            # 0.0 is the start frame of the video (start_offset_frames into the video)
            interpolated_distance = 0.0
            if self.backing:
                self.backing = False
                self.speed = 0
                self.backup_timeout = None

        # section = self.track_information.get_section(self.current_section)
        # if interpolated_distance > section.get_default_end_distance():
        #     interpolated_distance = section.get_default_end_distance()

        if self.backing:
            if self.backup_timeout is not None:
                if now >= self.backup_timeout:
                    self.backing = False
                    self.speed = 0
                    self.backup_timeout = None
                #self.distance += self.speed * diff
            self.speed_variable.set(str(int(self.speed * 3.6)))
            self.window.after(100, self.update_speed)
            return

        drag_constant = 0.02  # Might mean that max speed is about 150km/h
        car_mass = 2500
        max_car_gas_force = 745 * 120  # 120hp
        max_car_brake_force = 745 * 300  # Might be a strange way to calculate brake force, but why not try...
        current_force = 0
        if self.current_gas > 0:
            current_force = self.current_gas * max_car_gas_force
        elif self.current_brake > 0:
            current_force = -(self.current_brake * max_car_brake_force)
        acc = current_force / car_mass
        drag_force = self.speed * self.speed * drag_constant
        drag_acc = drag_force  # / car_mass

        delta = (
                            acc - drag_acc) * 0.1 / 8  # 0.1sec, but the acceleration was too quick for some reason, so divide by 10
        self.speed += delta

        # generellt motstånd
        self.speed -= 0.1
        if self.speed < 0:
            self.speed = 0
        # Max speed of 75 km/h just to help reduce video bugs
        if self.speed * 3.6 > 75.0:
            self.speed = 75.0 / 3.6

        self.speed_variable.set(str(int(self.speed * 3.6)))

        self.window.after(100, self.update_speed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='The steering GUI')
    parser.add_argument("-p", "--port", type=int, help="UDP port of the main client", required=True)
    parser.add_argument("-c", "--client_index", type=int, help="Client index, used in communication", required=True)
    parser.add_argument("-u", "--user_id", type=int, help="User ID", required=True)
    parser.add_argument("-r", "--rally_configuration", type=str, help="Path to the rally configuration to use",
                        required=True)
    parser.add_argument("-d", "--data_path", type=str, help="Path to root of where rally data is stored",
                        required=True)
    args = parser.parse_args()

    rally_configuration = ClientRallyConfig(args.rally_configuration, args.data_path)
    track_information = rally_configuration.track_information

    steering_gui = SteeringWindow(args.client_index, track_information)
    steering_gui.run()
