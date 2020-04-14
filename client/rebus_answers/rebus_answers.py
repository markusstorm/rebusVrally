import argparse
import tkinter.font
from functools import partial
from tkinter import Tk, Frame, Label, StringVar, Entry, Text, END, W, DISABLED, messagebox

from rally.common.rally_config import RallyConfiguration
from rally.common.subclient_communicator import SubClientCommunicator
from rally.protocol import clientprotocol_pb2


parser = argparse.ArgumentParser(description='Rebus report sheet')
parser.add_argument("-p", "--port", type=int, help="UDP port of the main client", required=True)
parser.add_argument("-c", "--client_index", type=int, help="Client index, used in communication", required=True)
parser.add_argument("-u", "--user_id", type=int, help="User ID", required=True)
args = parser.parse_args()

rally_configuration = RallyConfiguration()
track_information = rally_configuration.track_information

window = None
section_number_to_text_entry = {}
known_texts = {} # section number -> string


def on_status_updates(status_information):
    focus_entry = None
    if window is not None:
        try:
            focus_entry = window.focus_get()
        except RuntimeError:
            pass

    for section in status_information.rebus_answers:
        answer = status_information.rebus_answers[section]
        txt_entry = None
        if section in section_number_to_text_entry:
            txt_entry = section_number_to_text_entry[section]
        if txt_entry is not None:
            if txt_entry != focus_entry:
                txt_entry.delete("1.0", END)
                txt_entry.insert(END, answer)


sub_client_communicator = SubClientCommunicator(args, status_receiver=on_status_updates)
sub_client_communicator.start()


def send_rebus_answer(section, answer):
    global args
    client_to_server = clientprotocol_pb2.ClientToServer()
    client_to_server.counter = args.client_index
    client_to_server.set_rebus_answer.SetInParent()
    client_to_server.set_rebus_answer.section = section
    client_to_server.set_rebus_answer.answer = answer
    sub_client_communicator.send(client_to_server)


def rebus_key_release(section, textbox, *args, **kwargs):
    new_text = textbox.get(1.0, END)
    changed = True
    if section in known_texts:
        old_text = known_texts[section]
        if new_text == old_text:
            changed = False
    known_texts[section] = new_text
    if changed:
        send_rebus_answer(section, new_text)


window = Tk()
window.title("Rebusblankett")


for section_number in track_information.get_all_section_numbers():
    part_frame = Frame(window)

    Label(part_frame, text="R" + str(section_number)).grid(row=0, column=0, sticky=W)
    rebus_text = Text(part_frame, height=5, width=80)
    rebus_text.bind("<KeyRelease>", partial(rebus_key_release, section_number, rebus_text))
    section_number_to_text_entry[section_number] = rebus_text
    rebus_text.grid(row=1, column=0, sticky=W)

    part_frame.grid(row=section_number, column=0)

window.mainloop()
