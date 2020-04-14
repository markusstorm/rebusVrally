import argparse
import tkinter.font
from functools import partial
from tkinter import Tk, Frame, Label, StringVar, Entry, Text, END, W, DISABLED, messagebox

from rally.common.rally_config import RallyConfiguration
from rally.common.subclient_communicator import SubClientCommunicator
from rally.protocol import clientprotocol_pb2


parser = argparse.ArgumentParser(description='The steering GUI')
parser.add_argument("-p", "--port", type=int, help="UDP port of the main client", required=True)
parser.add_argument("-c", "--client_index", type=int, help="Client index, used in communication", required=True)
parser.add_argument("-u", "--user_id", type=int, help="User ID", required=True)
args = parser.parse_args()

rally_configuration = RallyConfiguration()
track_information = rally_configuration.track_information

all_plate_variables = {}
all_photo_variables = {}

all_plate_entries = {}
all_photo_entries = {}

name_to_entry_map = {}
stringvar_and_entry_list = []

current_rally_stage = None

def find_entry_from_stringvar(var):
    for pair in stringvar_and_entry_list:
        if pair.var == var:
            return pair.entry
    return None

window = None

class VarEntryPair:
    def __init__(self, var, entry):
        self.var = var
        self.entry = entry


def send_photo_answer(section, index, answer):
    global args
    client_to_server = clientprotocol_pb2.ClientToServer()
    client_to_server.counter = args.client_index
    client_to_server.set_photo_answer.SetInParent()
    client_to_server.set_photo_answer.section = section
    client_to_server.set_photo_answer.index = index
    client_to_server.set_photo_answer.answer = answer
    sub_client_communicator.send(client_to_server)


def send_plate_answer(section, index, answer):
    global args
    client_to_server = clientprotocol_pb2.ClientToServer()
    client_to_server.counter = args.client_index
    client_to_server.set_plate_answer.SetInParent()
    client_to_server.set_plate_answer.section = section
    client_to_server.set_plate_answer.index = index
    client_to_server.set_plate_answer.answer = answer
    sub_client_communicator.send(client_to_server)

def disenable_entries_for_sections(sections, enable):
    config = "disabled"
    if enable:
        config = "normal"
    for section in sections:
        if section in all_plate_entries:
            entries = all_plate_entries[section]
            for entry in entries:
                entry.config(state=config)
        if section in all_photo_entries:
            entries = all_photo_entries[section]
            for entry in entries:
                entry.config(state=config)

def disable_all_entries():
    disenable_entries_for_sections(track_information.get_all_section_numbers(), False)

def enable_all_entries():
    disenable_entries_for_sections(track_information.get_all_section_numbers(), True)

def enable_afternoon_entries():
    disenable_entries_for_sections(track_information.get_afternoon_section_numbers(), True)


latest_photo_answers_seq = -1
latest_plate_answers_seq = -1
def on_status_updates(status_information):
    focus_entry = None
    if window is not None:
        try:
            focus_entry = window.focus_get()
        except RuntimeError:
            pass

    global current_rally_stage
    if status_information.rally_stage != current_rally_stage:
        current_rally_stage = status_information.rally_stage

        if current_rally_stage == clientprotocol_pb2.ServerPositionUpdate.RallyStage.ENDED:
            disable_all_entries()
        elif current_rally_stage == clientprotocol_pb2.ServerPositionUpdate.RallyStage.NOT_STARTED or \
             current_rally_stage == clientprotocol_pb2.ServerPositionUpdate.RallyStage.MORNING:
            enable_all_entries()
        elif current_rally_stage != clientprotocol_pb2.ServerPositionUpdate.RallyStage.ENDED:
            disable_all_entries()
            enable_afternoon_entries()

    global latest_plate_answers_seq
    if status_information.plate_answers_seq != latest_plate_answers_seq:
        latest_plate_answers_seq = status_information.plate_answers_seq
        for answer in status_information.plate_answers:
            if answer.section in all_plate_variables:
                section_variables = all_plate_variables[answer.section]
                if 0 <= answer.index < len(section_variables):
                    variable = section_variables[answer.index]
                    if variable is not None:
                        entry = find_entry_from_stringvar(variable)
                        if entry is not None:
                            if entry != focus_entry:
                                variable.set(answer.answer)

    global latest_photo_answers_seq
    if status_information.photo_answers_seq != latest_photo_answers_seq:
        latest_photo_answers_seq = status_information.photo_answers_seq
        for answer in status_information.photo_answers:
            if answer.section in all_photo_variables:
                section_variables = all_photo_variables[answer.section]
                if 0 <= answer.index < len(section_variables):
                    variable = section_variables[answer.index]
                    if variable is not None:
                        entry = find_entry_from_stringvar(variable)
                        if entry is not None:
                            if entry != focus_entry:
                                variable.set(answer.answer)

def plate_text_changed(section, index, variable, entry, *args, **kwargs):
    if window.focus_get() != entry:
        return
    txt = variable.get()
    #print("Text changed to {0}".format(txt))
    if txt is None:
        txt = ""
    txt = txt.strip()
    send_plate_answer(section, index, txt)


def photo_text_changed(section, index, variable, entry, *args, **kwargs):
    if window.focus_get() != entry:
        return
    txt = variable.get()
    #print("Photo text changed to {0}".format(txt))
    if txt is None or len(txt) == 0:
        txt = "0"
    txt = txt.strip()
    i = 0
    try:
        i = int(txt)
    except ValueError:
        variable.set("")
        messagebox.showerror("Ogiltligt foto", "Foton måste vara bara siffror")
    send_photo_answer(section, index, i)


sub_client_communicator = SubClientCommunicator(args, status_receiver=on_status_updates)
sub_client_communicator.start()

window = Tk()
window.title("Plockblankett")

messages_text = Text(window, height=5, width=80)
messages_text.insert(END,
                     "Fotoplock och tallriksplock redovisas på denna blankett.\nSkriv tallrikarnas bokstäver i ringarna, och fotonas nummer i rektanglarna.\nSkriv på rätt rad för att visa mellan vilka kontroller ni hittade plocket.\nPlocken skall nedtecknas i rätt ordning.")
messages_text.config(state=DISABLED)
messages_text.grid(row=0, column=0)

FontOfEntryList = tkinter.font.Font(family="Calibri", size=20)

sections = track_information.get_section_titles()

all_entries_frame = Frame(window)
row_counter = 1
entry_name_counter = 0
for section_number in range(1, len(sections)+1):
    part_frame = Frame(all_entries_frame)
    Label(part_frame, text=sections[section_number]).grid(row=0, column=0, sticky=W)
    plock_frame = Frame(part_frame)
    plock_frame.grid(row=1, column=0)

    Label(plock_frame, text="Tallrikar").grid(row=0, column=0)
    Label(plock_frame, text="Fotoplock").grid(row=1, column=0)

    plate_variables = []
    plate_entries = []
    photo_variables = []
    photo_entries = []

    for i in range(0, 10):
        plate_var = StringVar()
        plate_variables.append(plate_var)
        name = str(entry_name_counter)
        plate_entry = Entry(plock_frame, textvariable=plate_var, borderwidth=1, width=3, font=FontOfEntryList, name=name)
        plate_entry.config(state="disabled")
        plate_var.trace_add("write", partial(plate_text_changed, section_number, i, plate_var, plate_entry))
        name_to_entry_map[name] = plate_entry
        #entry_to_stringvar_map[plate_entry] = plate_var
        #stringvar_to_entry_map[plate_var] = plate_entry
        stringvar_and_entry_list.append(VarEntryPair(plate_var, plate_entry))
        entry_name_counter += 1
        plate_entry.grid(row=0, column=i+1)
        plate_entries.append(plate_entry)

    for i in range(0, 10):
        photo_var = StringVar()
        photo_variables.append(photo_var)
        name = str(entry_name_counter)
        photo_entry = Entry(plock_frame, textvariable=photo_var, borderwidth=1, width=2, font=FontOfEntryList, name=name)
        photo_entry.config(state="disabled")
        photo_var.trace_add("write", partial(photo_text_changed, section_number, i, photo_var, photo_entry))
        name_to_entry_map[name] = photo_entry
        #entry_to_stringvar_map[photo_entry] = photo_var
        #stringvar_to_entry_map[photo_var] = photo_entry
        stringvar_and_entry_list.append(VarEntryPair(photo_var, photo_entry))
        entry_name_counter += 1
        photo_entry.grid(row=1, column=i+1)
        photo_entries.append(photo_entry)

    all_plate_variables[section_number] = plate_variables.copy()
    all_plate_entries[section_number] = plate_entries.copy()
    all_photo_variables[section_number] = photo_variables.copy()
    all_photo_entries[section_number] = photo_entries.copy()

    part_frame.grid(row=section_number, column=0)

all_entries_frame.grid(row=1, column=0, sticky=W)

window.mainloop()
