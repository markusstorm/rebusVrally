import argparse
from tkinter import Tk, Frame, Label, StringVar, Entry, Text, END, W, DISABLED, messagebox, Button
from tkinter.ttk import Combobox

from client.common.client_config import ClientRallyConfig
from rally.common.subclient_communicator import SubClientCommunicator
from rally.protocol import clientprotocol_pb2

parser = argparse.ArgumentParser(description='Test rebus solutions')
parser.add_argument("-p", "--port", type=int, help="UDP port of the main client", required=True)
parser.add_argument("-c", "--client_index", type=int, help="Client index, used in communication", required=True)
parser.add_argument("-u", "--user_id", type=int, help="User ID", required=True)
parser.add_argument("-r", "--rally_configuration", type=str, help="Path to the rally configuration to use", required=False)
parser.add_argument("-d", "--data_path", type=str, help="Path to root of where rally data is stored", required=True)
args = parser.parse_args()

rally_configuration = ClientRallyConfig(args.rally_configuration, args.data_path)
track_information = rally_configuration.track_information

window = None
fully_started = False
latest_status_information = None
terminate = False
my_answers = {}
current_text = ""


class MyAnswer:
    def __init__(self, txt, east, north):
        self.txt = txt
        self.east = east
        self.north = north


def update_solution_text(cb_changed):
    if latest_status_information is None:
        return
    if not fully_started:
        return

    global current_text

    if cb_changed:
        solution_var.set("")
        east_var.set("")
        north_var.set("")
        answer_text.delete("1.0", END)
        current_text = ""

    section = int(combo_select_rebus_number.get())
    for key in latest_status_information.rebus_solutions:
        solution = latest_status_information.rebus_solutions[key]

        if solution.section == section:
            s = ""
            s += "{0}\n".format(solution.target_description)
            if solution.target_east > 0 and solution.target_north > 0:
                s += "Du ska åka till (ungefär) {0} öst, {1} nord.\n".format(solution.target_east, solution.target_north)
                if cb_changed:
                    solution_var.set(solution.solution)
                    east_var.set(solution.east)
                    north_var.set(solution.north)
            else:
                if cb_changed:
                    if section in my_answers:
                        my_answer = my_answers[section]
                        solution_var.set(my_answer.txt)
                        east_var.set(my_answer.east)
                        north_var.set(my_answer.north)

            if solution.target_picture is not None and len(solution.target_picture) > 0:
                s += "Inzoomad bild på nästa delmål: {0}".format(solution.target_picture)
            if s == current_text:
                return
            current_text = s
            answer_text.delete("1.0", END)
            answer_text.insert(END, s)
            return


def on_status_updates(status_information):
    if terminate:
        return

    global latest_status_information
    latest_status_information = status_information
    update_solution_text(False)

    already_solved = False
    rebus_number = int(combo_select_rebus_number.get())
    if rebus_number in latest_status_information.rebus_solutions:
        solution = latest_status_information.rebus_solutions[rebus_number]
        if solution.target_east > 0 and solution.target_north > 0:
            already_solved = True

    if status_information.rebus_solutions_locked or already_solved:
        test_solution_button["state"] = "disabled"
    else:
        test_solution_button["state"] = "normal"


sub_client_communicator = SubClientCommunicator(args, status_receiver=on_status_updates)
sub_client_communicator.start()


def send_rebus_answer(section, answer, east, north):
    global args
    my_answers[section] = MyAnswer(answer, east, north)
    client_to_server = clientprotocol_pb2.ClientToServer()
    client_to_server.counter = args.client_index
    client_to_server.test_rebus_solution.SetInParent()
    client_to_server.test_rebus_solution.section = section;
    client_to_server.test_rebus_solution.answer = answer;
    client_to_server.test_rebus_solution.map_east = east;
    client_to_server.test_rebus_solution.map_north = north;
    sub_client_communicator.send(client_to_server)


window = Tk()
window.title("Testa rebuslösning")
combo_select_rebus_number = None




def on_section_cb_changed(data):
    update_solution_text(True)


def on_test_solution_clicked():
    section = int(combo_select_rebus_number.get())
    answer = solution_var.get().strip()
    east = None
    north = None
    try:
        east = int(east_var.get().strip())
    except ValueError:
        messagebox.showerror("Ogiltligt värde", "Öst måste vara ett heltal", parent=window)
        return

    try:
        north = int(north_var.get().strip())
    except ValueError:
        messagebox.showerror("Ogiltligt värde", "Nord måste vara ett heltal", parent=window)
        return

    if len(answer) == 0 or east is None or north is None:
        messagebox.showerror("Ogiltligt värde", "Du måste ange lösning, öst och nord", parent=window)
        return

    #TODO: validate east/north according to current map

    send_rebus_answer(section, answer, east, north)


messages_text = Text(window, height=6, width=80)
messages_text.insert(END,
                     "Använd denna funktion för att skicka in din lösning på en rebus.\n"
                     "Om lösningen är korrekt får du information om vart ni ska åka härnäst.\n"
                     "När rebusen är inskickad kan det ta någon sekund innan resultatet kommer.\n"
                     "Det går bara att använda funktionen en gång per minut.\n"
                     "Ange en koordinat från kartan så nära lösningen som möjligt.\n"
                     "OBS! Masstestning kan ge straffprickar!"
                     )
messages_text.config(state=DISABLED)
messages_text.grid(row=0, column=0)

f_row1 = Frame(window)
Label(f_row1, text="Rebus nummer").grid(row=0, column=0)
combo_select_rebus_number = Combobox(f_row1, values=track_information.get_all_section_numbers())
combo_select_rebus_number.bind("<<ComboboxSelected>>", on_section_cb_changed)
combo_select_rebus_number.current(0)
combo_select_rebus_number.grid(row=0, column=1)
f_row1.grid(row=1, column=0, sticky=W, pady=(20, 0))

f_row2 = Frame(window)
Label(f_row2, text="Lösning").grid(row=0, column=0)
solution_var = StringVar()
solution_entry = Entry(f_row2, textvariable=solution_var, borderwidth=1, width=30)
solution_entry.grid(row=0, column=1)
f_row2.grid(row=2, column=0, sticky=W)

f_row3 = Frame(window)
Label(f_row3, text="Plats på kartan").grid(row=0, column=0)
east_var = StringVar()
east_entry = Entry(f_row3, textvariable=east_var, borderwidth=1, width=3)
east_entry.grid(row=0, column=1)
Label(f_row3, text="Öst, ").grid(row=0, column=2)
north_var = StringVar()
north_entry = Entry(f_row3, textvariable=north_var, borderwidth=1, width=3)
north_entry.grid(row=0, column=3)
Label(f_row3, text="Nord").grid(row=0, column=4)
f_row3.grid(row=3, column=0, sticky=W)

test_solution_button = Button(window, text="Testa lösningen", command=on_test_solution_clicked)
test_solution_button.grid(row=4, column=0, sticky=W)

answer_title_label = Label(window, text="Här kommer svaret när du har tryckt på knappen ovan:")
answer_title_label.grid(row=5, column=0, sticky=W, pady=(20, 0))

answer_text = Text(window, height=5, width=80)
answer_text.insert(END, "")
answer_text.grid(row=6, column=0)

fully_started = True
window.mainloop()
terminate = True
sub_client_communicator.stop()
