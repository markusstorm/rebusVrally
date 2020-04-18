import argparse
from tkinter import *
from tkinter import messagebox as messagebox

from client.common.client_config import ClientRallyConfig
from rally.common.subclient_communicator import SubClientCommunicator
from rally.protocol import clientprotocol_pb2


parser = argparse.ArgumentParser(description='The fish bone GUI')
parser.add_argument("-p", "--port", type=int, help="UDP port of the main client", required=True)
parser.add_argument("-c", "--client_index", type=int, help="Client index, used in communication", required=True)
parser.add_argument("-u", "--user_id", type=int, help="User ID", required=True)
parser.add_argument("-r", "--rally_configuration", type=str, help="Path to the rally configuration to use", required=False)
parser.add_argument("-d", "--data_path", type=str, help="Path to root of where rally data is stored",
                    required=True)
args = parser.parse_args()

rally_configuration = ClientRallyConfig(args.rally_configuration, args.data_path)
track_information = rally_configuration.track_information


class Rebus:
    NORMAL = 0
    HELP = 1
    SOLUTION = 2
    rebus_types = [NORMAL, HELP, SOLUTION]

    BUTTON_HEIGHT = 5
    BUTTON_WIDTH = 30

    def __init__(self, parent, section_number, rebus_type, rebus_window):
        self.rebus_window = rebus_window
        text_formats = {Rebus.NORMAL: "Rebus {0} (R{0})",
                        Rebus.HELP: "Hjälp till R{0}",
                        Rebus.SOLUTION: "Nödlösning till R{0}"}
        self.text = text_formats[rebus_type].format(section_number)

        costs = {Rebus.NORMAL: 0,
                 Rebus.HELP: 25,
                 Rebus.SOLUTION: 45}
        self.cost = costs[rebus_type]

        self.extra_text = "(Dyker upp här när ni hittar den)"
        if section_number == 1: #TODO: use config instead
            self.extra_text = "(Dyker upp här när rallyt startar)"
        if section_number == 5: #TODO: use config instead
            self.extra_text = "(Dyker upp här efter lunch)"

        self.rebus_type = rebus_type
        self.parent = parent
        self.section_number = section_number

        self.solution_label = None
        self.extra_label = None
        self.button = None
        self.known_text = ""
        self.solution_entry = ""

        self.layout()

    def layout(self):
        if self.rebus_type == Rebus.NORMAL:
            # get text from rebus status
            f = Frame(self.parent)
            self.solution_label = Label(f, text=self.text)
            self.solution_label.grid(row=0, column=0)
            self.extra_label = Label(f, text=self.extra_text)
            self.extra_label.grid(row=1, column=0)
            f.grid(row=self.section_number, column=Rebus.NORMAL)
        else:
            self.button = Button(self.parent, text=self.text, width=Rebus.BUTTON_WIDTH, height=Rebus.BUTTON_HEIGHT,  command=self.onClick)
            self.button.grid(row=self.section_number, column=self.rebus_type)

    def onClick(self):
        if messagebox.askyesno("Använda sax?", "Är du säker på att du vill klippa {0}?\n(Det kostar {1} prickar)".format(self.text, self.cost), default="no"):
            self.remove_button()
            self.rebus_window.request_a_solution(self.section_number, self.rebus_type)
            print("Nu är det klippt! %s"%(self.text))

    def remove_button(self):
        color = self.button.cget("bg")
        self.button.destroy()
        self.button = None
        if self.extra_label is not None:
            self.extra_label.destroy()
            self.extra_label = None
        self.solution_label = Label(self.parent, text=self.text, width=Rebus.BUTTON_WIDTH, height=Rebus.BUTTON_HEIGHT)
        self.solution_label.grid(row=self.section_number, column=self.rebus_type)
        self.parent.configure(bg=color)

    def set_text(self, txt):
        if self.button is not None:
            self.remove_button()

        if self.extra_label is not None:
            self.extra_label.destroy()
            self.extra_label = None

        if self.known_text == txt:
            return

        if "://" in txt:
            if self.solution_label is not None:
                self.solution_label.destroy()
            self.solution_entry = Entry(self.parent, width=Rebus.BUTTON_WIDTH)
            self.solution_entry.grid(row=self.section_number, column=self.rebus_type)
            self.solution_entry.delete(0, END)
            self.solution_entry.insert(0, txt)
            self.solution_entry["state"] = "readonly"
        else:
            self.solution_label["text"] = txt
        self.known_text = txt


class RebusWindow:
    def __init__(self):
        self.terminate = False
        self.all_rebuses = []

        self.window = Tk()
        self.window.title("Rebusar och fiskben")
        self.layout()

        self.sub_client_communicator = SubClientCommunicator(args, status_receiver=self.on_status_updates)
        self.sub_client_communicator.start()

        self.window.mainloop()
        self.terminate = True
        self.sub_client_communicator.stop()

    def layout(self):
        messages_text = Text(self.window, height=5, width=80)
        messages_text.insert(END,
                             "I detta fönstret dyker rebusar upp när förmiddagen och eftermiddagen börjar,\nsamt när ni hittar rebusar längs med vägen.\n"
                             "Om ni inte kan lösa en rebus kan ni \"klippa upp\" en hjälprebus (kostar \n25 prickar) eller lösningen (kostar 45 prickar).\n"
                             "Klicka på knapparna för att klippa upp motsvarande hjälp/lösning."
                             )
        messages_text.config(state=DISABLED)
        messages_text.grid(row=0, column=0)

        rest = Frame(self.window)
        for section_number in track_information.get_all_section_numbers():
            rebus_frame = Frame(rest, pady=3, padx=3)
            rebus_frame.grid(row=section_number, column=0)
            rebus = Rebus(rebus_frame, section_number, Rebus.NORMAL, self)
            self.all_rebuses.append(rebus)

            help_frame = Frame(rest, bg="black", pady=3, padx=3)
            help_frame.grid(row=section_number, column=1)
            help_rebus = Rebus(help_frame, section_number, Rebus.HELP, self)
            self.all_rebuses.append(help_rebus)

            solution_frame = Frame(rest, bg="black", pady=3, padx=3)
            solution_frame.grid(row=section_number, column=2)
            solution = Rebus(solution_frame, section_number, Rebus.SOLUTION, self)
            self.all_rebuses.append(solution)
        rest.grid(row=1, column=0)

    def get_rebus(self, section, rebus_type):
        for rebus in self.all_rebuses:
            if rebus.section_number == section and rebus.rebus_type == rebus_type:
                return rebus
        return None

    def on_status_updates(self, status_information):
        if self.terminate:
            return
        for rebus_status in status_information.rebus_statuses.rebus_statuses.values():
            #print("{0}".format(rebus_status))
            for rebus_type in Rebus.rebus_types:
                txt, extra = rebus_status.get_text(rebus_type)
                if txt is None or len(txt) == 0:
                    continue
                if extra is not None:
                    txt = "{0}\n{1}".format(txt, extra)
                if rebus_type == Rebus.SOLUTION:
                    txt = "{0}\n{1}".format(txt, "\nSkriv in detta i GUI:t 'Testa rebuslösning'\n för att få reda på vart ni ska åka!")
                rebus = self.get_rebus(rebus_status.section, rebus_type)
                if rebus is not None:
                    rebus.set_text(txt)

    def request_a_solution(self, section, rebus_type):
        global args
        client_to_server = clientprotocol_pb2.ClientToServer()
        client_to_server.counter = args.client_index
        client_to_server.open_rebus_solution.SetInParent()
        client_to_server.open_rebus_solution.user_id = args.user_id
        client_to_server.open_rebus_solution.section = section
        if rebus_type == Rebus.HELP:
            client_to_server.open_rebus_solution.open_help = True
        else:
            client_to_server.open_rebus_solution.open_solution = True
        self.sub_client_communicator.send(client_to_server)


rebus_window = RebusWindow()
