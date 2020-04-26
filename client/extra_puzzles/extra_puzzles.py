import argparse
import tkinter
from functools import partial
from tkinter import Tk, Frame, Label, Text, END, DISABLED, NORMAL, Button, W, messagebox
import tkinter.font

from client.common.client_config import ClientRallyConfig
from rally.common.subclient_communicator import SubClientCommunicator
from rally.protocol import clientprotocol_pb2


class ExtraPuzzles:
    def __init__(self, args):
        self.client_index = args.client_index
        self.rally_configuration = ClientRallyConfig(args.rally_configuration, args.data_path)
        self.track_information = self.rally_configuration.track_information

        self.window = None
        self.latest_status_information = None
        self.terminate = False

        self.buttons = {}
        self.descriptions = {}

        self.layout()

        self.sub_client_communicator = SubClientCommunicator(args, status_receiver=self.on_status_updates)

    def run(self):
        self.sub_client_communicator.start()
        self.window.mainloop()
        self.terminate = True
        self.sub_client_communicator.stop()

    def layout(self):
        self.window = Tk()
        self.window.title("Extrauppgifter")

        messages_text = Text(self.window, height=2, width=80)
        messages_text.insert(END,
                             "Här hittar ni extrauppgifter som ni själva kan välja om ni vill ta er an.\n"
                             "När ni 'öppnar' en extrauppgift får ni en URL där uppgiften kan hämtas.\n"
                             )
        messages_text.config(state=DISABLED)
        messages_text.grid(row=0, column=0)

        title_font = tkinter.font.Font(family="Calibri", size=16)

        row = 1
        for extra_puzzle in self.rally_configuration.extra_puzzles.values():
            f = Frame(self.window)

            title_label = Label(f, text=extra_puzzle.title, font=title_font)
            title_label.grid(row=0, column=0, sticky=W)

            f2 = Frame(f)
            description = Text(f2, height=2, width=70)
            description.insert(END, extra_puzzle.description)
            description.config(state=DISABLED)
            description.grid(row=0, column=0, sticky=W)
            self.descriptions[extra_puzzle.id] = description
            open_task_button = Button(f2, text="Öppna", font=title_font, command=partial(self.on_open_puzzle, extra_puzzle))
            open_task_button.grid(row=0, column=1, sticky=W)
            self.buttons[extra_puzzle.id] = open_task_button

            f2.grid(row=1, column=0, sticky=W)

            f.grid(row=row, column=0, sticky=W)
            row += 1

    def on_status_updates(self, status_information):
        if self.terminate:
            return
        self.latest_status_information = status_information
        self.update_gui()

    def update_gui(self):
        if self.terminate:
            return
        if self.latest_status_information is None:
            return
        for puzzle_id in self.latest_status_information.extra_puzzles:
            instructions = self.latest_status_information.extra_puzzles[puzzle_id]
            if puzzle_id in self.buttons:
                button = self.buttons[puzzle_id]
                button["state"] = "disabled"
            if puzzle_id in self.descriptions:
                description_obj = self.descriptions[puzzle_id]
                current_text = description_obj.get(1.0, END)
                if current_text.strip() != instructions.strip():
                    description_obj.config(state=NORMAL)
                    description_obj.delete("1.0", END)
                    description_obj.insert(END, instructions)
                    description_obj.config(state=DISABLED)

    def on_open_puzzle(self, extra_puzzle):
        if messagebox.askyesno("Öppna pyssel?", extra_puzzle.question, default="no"):
            self.send_request_to_open(extra_puzzle)

    def send_request_to_open(self, extra_puzzle):
        client_to_server = clientprotocol_pb2.ClientToServer()
        client_to_server.counter = self.client_index
        client_to_server.open_extra_puzzle.SetInParent()
        client_to_server.open_extra_puzzle.puzzle_id = extra_puzzle.id
        self.sub_client_communicator.send(client_to_server)


parser = argparse.ArgumentParser(description='Show extra puzzles to the user')
parser.add_argument("-p", "--port", type=int, help="UDP port of the main client", required=True)
parser.add_argument("-c", "--client_index", type=int, help="Client index, used in communication", required=True)
parser.add_argument("-u", "--user_id", type=int, help="User ID", required=True)
parser.add_argument("-r", "--rally_configuration", type=str, help="Path to the rally configuration to use", required=False)
parser.add_argument("-d", "--data_path", type=str, help="Path to root of where rally data is stored", required=True)
args = parser.parse_args()

extra_puzzles = ExtraPuzzles(args)
extra_puzzles.run()
