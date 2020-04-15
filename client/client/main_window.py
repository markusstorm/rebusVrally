from tkinter import Label, Button, Frame, Toplevel, Text, messagebox, END, N
from tkinter.ttk import Combobox

from PIL import ImageTk, Image

from client.client.external_processes import SubProcesses
from client.client.subprocess_communicator import SubProcessCommunicator
from rally.protocol import clientprotocol_pb2


class MainWindow:
    def __init__(self, rally_configuration, server_conn, running_as_exe):
        self.running_as_exe = running_as_exe
        self.subprocess_communicator = SubProcessCommunicator(server_conn)
        self.subprocess_communicator.start()
        self.server_connection = server_conn
        # server_conn.report_lost_connection = self.on_lost_connection
        # server_conn.message_receiver = self.on_message_received
        self.rally_configuration = rally_configuration
        self.sub_processes = SubProcesses(self.subprocess_communicator, self.rally_configuration, self.running_as_exe, self.server_connection.temporary_config_file)
        self.positions_map = {"Utanför bussen": 0,
                              "Förare": 1,
                              "Kartläsare": 2,
                              "Fram höger": 3,
                              "Mitten vänster": 4,
                              "Protokollförare": 5,
                              "Mitten höger": 6,
                              "Bak vänster": 7,
                              "Bak mitten": 8,
                              "Bak höger": 9}
        self.all_positions = ["Utanför bussen",
                              "Förare",
                              "Kartläsare",
                              "Fram höger",
                              "Mitten vänster",
                              "Protokollförare",
                              "Mitten höger",
                              "Bak vänster",
                              "Bak mitten",
                              "Bak höger"]
        self.main_window = None
        self.combo_select_seating = None
        self.placing_label = None
        self.placing_button = None
        self.rebus_button = None
        self.seats = []
        self.messages_text = None
        self.minibus_img = None

        self.layout()

        self.server_connection.start_client_loop(self.on_lost_connection, self.on_message_received, self.subprocess_communicator)

    def run(self):
        self.main_window.mainloop()
        self.main_window.destroy()

    def layout(self):
        self.main_window = Toplevel()
        #self.main_window.withdraw()
        self.main_window.title(self.rally_configuration.title)

        self.minibus_img = ImageTk.PhotoImage(Image.open("minibus.png"))
        w2 = self.minibus_img.width()
        h2 = self.minibus_img.height()

        f_bus = Frame(self.main_window, width=w2, height=480)
        background_label2 = Label(f_bus, image=self.minibus_img)
        # background_label2.place(x=0, y=0, relwidth=1, relheight=1)
        background_label2.grid(row=0, column=0, sticky=N)
        f_bus.grid(row=0, column=0, sticky=N)

        f_placing = Frame(f_bus)
        self.placing_label = Label(f_placing, text="Välj plats i bussen:")
        self.placing_label.grid(row=0, column=0)
        self.combo_select_seating = Combobox(f_placing, values=self.all_positions)
        self.combo_select_seating.current(0)
        self.combo_select_seating.grid(row=1, column=0)
        self.combo_select_seating.bind("<<ComboboxSelected>>", self.on_placing_cb_changed)
        f_placing.grid(row=1, column=0, sticky=N)

        self.placing_button = Button(f_placing, command=self.on_select_placing, text="Aktivera vald plats i bussen")
        self.placing_button.grid(row=2, column=0)
        self.rebus_button = Button(f_placing, command=self.on_search_for_rebus, text="Leta efter rebus här")
        self.rebus_button.grid(row=3, column=0)

        seat1 = Label(background_label2, text="")
        seat1.place(x=35, y=130)
        seat2 = Label(background_label2, text="")
        seat2.place(x=75, y=150)
        seat3 = Label(background_label2, text="")
        seat3.place(x=110, y=170)

        seat4 = Label(background_label2, text="")
        seat4.place(x=35, y=195)
        seat5 = Label(background_label2, text="")
        seat5.place(x=75, y=215)
        seat6 = Label(background_label2, text="")
        seat6.place(x=110, y=235)

        seat7 = Label(background_label2, text="")
        seat7.place(x=35, y=270)
        seat8 = Label(background_label2, text="")
        seat8.place(x=75, y=290)
        seat9 = Label(background_label2, text="")
        seat9.place(x=110, y=310)

        self.seats = [None, seat1, seat2, seat3, seat4, seat5, seat6, seat7, seat8, seat9]

        self.messages_text = Text(self.main_window, height=40, width=45)
        self.messages_text.grid(row=0, column=1)

        self.main_window.protocol("WM_DELETE_WINDOW", self.close_main_window)

        self.main_window.after(1, self.update_main_gui)

    def on_placing_cb_changed(self, data):
        position_value = self.positions_map[self.combo_select_seating.get()]
        #global server_connection
        client_to_server = clientprotocol_pb2.ClientToServer()
        client_to_server.select_seat.SetInParent()
        client_to_server.select_seat.user_id = self.server_connection.status_information.user_id
        client_to_server.select_seat.seat_index = position_value
        # print("Send message")
        self.server_connection.send_message_to_server(client_to_server)

    def on_select_placing(self):
        self.sub_processes.stop_processes()
        self.sub_processes.start_processes(self.server_connection.status_information.get_my_seat())

    def on_search_for_rebus(self):
        client_to_server = clientprotocol_pb2.ClientToServer()
        client_to_server.search_for_rebus.SetInParent()
        client_to_server.search_for_rebus.dummy = 0;
        self.server_connection.send_message_to_server(client_to_server)
        self.rebus_button["text"] = "Letar efter rebus"
        self.rebus_button["state"] = "disabled"

    def update_main_gui(self):
        speed = self.server_connection.get_current_speed()
        locked = speed != 0
        state = "normal"
        if locked:
            state = "disabled"
            self.placing_label["text"] = "Bussen står inte stilla"
        else:
            self.placing_label["text"] = "Välj plats i bussen:"
        if self.server_connection.status_information.looking_for_rebus:
            self.rebus_button["text"] = "Letar efter rebus"
            self.rebus_button["state"] = "disabled"
        else:
            self.rebus_button["text"] = "Leta efter rebus här"
            self.rebus_button["state"] = state
        self.combo_select_seating["state"] = state

        for i in range(1, 10):
            self.seats[i]["text"] = self.server_connection.status_information.seating[i].name

        self.main_window.after(1000, self.update_main_gui)

    def on_message_received(self, bc_message):
        # global messages_text
        if bc_message.HasField("date_time"):
            self.messages_text.insert(END, bc_message.date_time + "\n")
        if bc_message.HasField("message"):
            self.messages_text.insert(END, bc_message.message + "\n\n")
        self.messages_text.yview_pickplace("end")
        self.main_window.bell()

    def close_main_window(self):
        self.sub_processes.stop_processes()
        self.server_connection.stop()
        if self.main_window is not None:
            self.main_window.quit()

    def on_lost_connection(self):
        messagebox.showerror("Lost connection to server", "Lost connection to server", parent=self.main_window)
        self.close_main_window()
