import configparser
import os
import subprocess
import sys
from tkinter import messagebox, Button, Entry, StringVar, Label, Frame, Toplevel, filedialog, Tk
from tkinter.ttk import Combobox

from PIL import ImageTk, Image

from client.client.client_config_finder import ClientConfigFinder
from client.client.server_connection import ServerConnection
from client.common.client_config import ClientRallyConfig


class LoginWindow:
    def __init__(self, running_as_exe):
        self.running_as_exe = running_as_exe
        self.server_connection = None
        self.location = os.getcwd()
        self.current_login_configuration = None
        self.logged_in = False
        self.local_server_process = None
        self.config_parser = configparser.ConfigParser()
        self.config_parser.read("config.ini")

        self.login_window = Toplevel()
        self.login_window.title("Sötgötarnas rebus(V)rally")
        self.login_window.protocol("WM_DELETE_WINDOW", self.close_window)

        self.config_finder = ClientConfigFinder(ask_for_other_location=self.ask_for_other_location)
        if len(self.config_finder.rally_configs) == 0:
            messagebox.showerror("Konfigurationsfel", "Kan inte hitta någon rally-konfiguration", parent=self.login_window)
            self.login_window.destroy()
            return

        # Choose one configuration to start with
        self.current_login_configuration = self.config_finder.get_newest_config()
        self.rally_config = None

        self.photos_img = None
        self.background_label = None
        self.configuration_combobox = None
        self.difficulty_combobox = None
        self.server_sv = None
        self.serverEntry = None
        self.teamname_sv = None
        self.teamnameEntry = None
        self.password_sv = None
        self.passwordEntry = None
        self.username_sv = None
        self.usernameEntry = None
        self.loginButton = None
        self.login_frame = None
        self.entries = []

        self.layout()

    def __del__(self):
        if self.local_server_process is not None:
            self.local_server_process.terminate()
            self.local_server_process = None

    def run(self):
        self.login_window.mainloop()
        self.login_window.destroy()
        #TODO: destroy?

    def ask_for_other_location(self):
        guessed_dir = os.path.abspath(os.path.join(self.location, "../../"))
        filename = filedialog.askopenfilename(initialdir=guessed_dir, title = "Peka ut en rally-konfiguration (XML-fil)",filetypes = [["Rally configuration","*.xml"]])
        return filename

    def layout(self):
        self.background_label = Label(self.login_window, image=self.photos_img)
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)

        f = Frame(self.login_window, width=100, height=100)

        main_row = 0
        configLabel = Label(f, text="Välj rally").grid(row=main_row, column=0)
        current_index = 0
        titles = []
        for config in self.config_finder.rally_configs:
            if config == self.current_login_configuration:
                current_index = len(titles)
            titles.append(config.title)
        self.configuration_combobox = Combobox(f, values=self.config_finder.get_all_titles())
        self.configuration_combobox.current(current_index)
        self.configuration_combobox.bind("<<ComboboxSelected>>", self.on_rally_cb_changed)
        self.configuration_combobox.grid(row=main_row, column=1)

        main_row += 1
        difficultyLabel = Label(f, text="Välj svårighetsgrad").grid(row=main_row, column=0)
        self.difficulty_combobox = Combobox(f, values=self.current_login_configuration.get_difficulties())
        self.difficulty_combobox.current(0)
        #self.configuration_combobox.bind("<<ComboboxSelected>>", self.on_rally_cb_changed)
        self.difficulty_combobox.grid(row=main_row, column=1)

        main_row += 1
        serverLabel = Label(f, text="Server address").grid(row=main_row, column=0)
        self.server_sv = StringVar()
        self.server_sv.set("")
        self.serverEntry = Entry(f, textvariable=self.server_sv)
        self.serverEntry.grid(row=main_row, column=1)

        main_row += 1
        teamnameLabel = Label(f, text="Team Name").grid(row=main_row, column=0)
        self.teamname_sv = StringVar()
        self.teamname_sv.set("")
        self.teamnameEntry = Entry(f, textvariable=self.teamname_sv)
        self.teamnameEntry.grid(row=main_row, column=1)

        main_row += 1
        passwordLabel = Label(f, text="Password").grid(row=main_row, column=0)
        self.password_sv = StringVar()
        self.password_sv.set("")
        self.passwordEntry = Entry(f, textvariable=self.password_sv)
        self.passwordEntry.grid(row=main_row, column=1)

        main_row += 1
        usernameLabel = Label(f, text="User Name").grid(row=main_row, column=0)
        self.username_sv = StringVar()
        self.username_sv.set("")
        self.usernameEntry = Entry(f, textvariable=self.username_sv)
        self.usernameEntry.grid(row=main_row, column=1)

        main_row += 1
        self.loginButton = Button(f, text="Login", command=self.validateLoginFunction)
        self.loginButton.grid(row=main_row, column=1)

        self.entries = [self.configuration_combobox, self.serverEntry, self.teamnameEntry, self.passwordEntry,
                        self.usernameEntry, self.loginButton, self.difficulty_combobox]

        f.pack()
        f.update()
        self.login_frame = f

        self.update_layout()
        self.update_login_information()

    def update_layout(self):
        if self.current_login_configuration.login_background is not None:
            self.photos_img = ImageTk.PhotoImage(Image.open(self.current_login_configuration.login_background))
            w = self.photos_img.width()
            h = self.photos_img.height()
            self.login_window.geometry('%dx%d' % (w, h))
            self.background_label["image"] = self.photos_img

        if self.current_login_configuration.login_background is not None:
            self.login_frame.place(x=max((w - self.login_frame.winfo_width()) / 2, 0), y=max(0, h - self.login_frame.winfo_height()))
        else:
            self.login_frame.grid(row=0, column=0)

    def on_rally_cb_changed(self, data):
        self.update_login_information()

    def stop(self):
        self.current_login_configuration = None
        self.handle_local_server()

    def handle_local_server(self):
        if self.local_server_process is not None:
            self.local_server_process.terminate()
            self.local_server_process = None

        if self.current_login_configuration is None:
            return

        if not self.current_login_configuration.is_local:
            return

        if self.running_as_exe:
            args = ["server/server_main.exe", "-i", self.current_login_configuration.rally_id, "-l"]
            working_dir = os.path.join(os.getcwd(), "server")
        else:
            program = os.path.abspath(os.path.join(os.getcwd(), "../../server/server_main.py"))
            args = [sys.executable, program, "-i", self.current_login_configuration.rally_id, "-l"]
            working_dir = os.path.dirname(program)
        print("Starting local server, wait a second to let it start...")
        self.local_server_process = subprocess.Popen(args, cwd=working_dir)

    def update_login_information(self):
        selected_config_title = self.configuration_combobox.get()
        config = self.config_finder.get_rally_from_title(selected_config_title)
        if config is not None:
            self.current_login_configuration = config

        self.difficulty_combobox["values"] = self.current_login_configuration.get_difficulties()

        self.handle_local_server()

        # Get settings from the rally configuration
        server = self.current_login_configuration.default_server_address
        teamname = self.current_login_configuration.default_team_name
        password = self.current_login_configuration.default_password
        username = self.current_login_configuration.default_username

        # If the user has made changes before
        section_name = "login_{0}".format(self.current_login_configuration.rally_id)
        if section_name in self.config_parser:
            login_section = self.config_parser[section_name]
            if "server" in login_section and len(login_section["server"]) > 0:
                server = login_section["server"]
            if "teamname" in login_section and len(login_section["teamname"]) > 0:
                teamname = login_section["teamname"]
            if "password" in login_section and len(login_section["password"]) > 0:
                password = login_section["password"]
            if "username" in login_section and len(login_section["username"]) > 0:
                username = login_section["username"]
        self.server_sv.set(server)
        self.teamname_sv.set(teamname)
        self.password_sv.set(password)
        self.username_sv.set(username)

        self.update_layout()

        if not self.current_login_configuration.validate_data_files():
            message = ""
            for i in range(min(len(self.current_login_configuration.errors), 10)):
                message += self.current_login_configuration.errors[i] + "\n"
            messagebox.showwarning("Varning! Det saknas filer för denna konfiguration!", message, parent=self.login_window)

    def validateLoginFunction(self):
        server = self.server_sv.get().strip()
        teamname = self.teamname_sv.get().strip()
        password = self.password_sv.get().strip()
        username = self.username_sv.get().strip()

        if (len(server) > 0 and
                len(teamname) > 0 and
                len(username) > 0 and
                len(password) > 0):
            section_name = "login_{0}".format(self.current_login_configuration.rally_id)
            self.config_parser[section_name] = {}
            self.config_parser[section_name]["server"] = server
            self.config_parser[section_name]["teamname"] = teamname
            self.config_parser[section_name]["password"] = password
            self.config_parser[section_name]["username"] = username
            with open("config.ini", "w") as configout:
                self.config_parser.write(configout)
            for entry in self.entries:
                entry.config(state="disabled")

            difficulty = self.current_login_configuration.get_difficulty_from_string(self.difficulty_combobox.get())

            self.login(server, teamname, password, username, difficulty)

    def report_login_result(self, success, message):
        if success:
            self.logged_in = True
            self.login_window.quit()
            return

        self.server_connection = None

        messagebox.showerror("Fel vid inloggning", message, parent=self.login_window)

        for entry in self.entries:
            entry.config(state="normal")

    def close_window(self):
        self.login_window.quit()

# if status_information.user_id == 0:
#     exit_program = True
#     sys.exit(0)
    def login(self, server, teamname, password, username, difficulty):
        #print("Login")
        # Tries to login and the result is reported to report_login_result
        # If the login is unsuccessful, then the ServerConnection exits its thread
        self.server_connection = ServerConnection(server, teamname, password, username, self.report_login_result, None, difficulty)
        self.server_connection.start()

    def get_rally_config(self):
        if self.rally_config is None:
            if self.server_connection.temporary_config_file is None or len(self.server_connection.temporary_config_file) == 0:
                print("Error! Can't get information about the temporary file containing the client rally configuration!")
                return None
            data_path = self.current_login_configuration.location
            self.rally_config = ClientRallyConfig(self.server_connection.temporary_config_file, data_path)
        return self.rally_config
