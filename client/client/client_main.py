from tkinter import *

from client.client.login_window import LoginWindow
from client.client.main_window import MainWindow


if __name__ == '__main__':
    running_as_exe = False
    if len(sys.argv) > 0:
        if ".exe".casefold() in sys.argv[0].casefold():
            print("Running the program as an executable, this will affect how the sub clients are started")
            running_as_exe = True

    root = Tk()
    root.withdraw()

    login_window = LoginWindow(running_as_exe)
    if login_window.current_configuration is None:
        login_window.stop()
        sys.exit(1)
    login_window.run()

    if not login_window.logged_in:
        sys.exit(1)

    # NOW we are LOGGED IN!
    main_window = MainWindow(login_window.current_configuration, login_window.server_connection, running_as_exe)
    main_window.run()
    login_window.stop()