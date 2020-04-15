from tkinter import *

from client.client.login_window import LoginWindow
from client.client.main_window import MainWindow
from client.common.client_config import ClientRallyConfig

if __name__ == '__main__':
    running_as_exe = False
    if len(sys.argv) > 0:
        if ".exe".casefold() in sys.argv[0].casefold():
            print("Running the program as an executable, this will affect how the sub clients are started")
            running_as_exe = True

    root = Tk()
    root.withdraw()

    login_window = LoginWindow(running_as_exe)
    if login_window.current_login_configuration is None:
        # Unable to find a login configuration, so can't contact any servers
        login_window.stop()
        sys.exit(1)
    login_window.run()

    if not login_window.logged_in:
        login_window.stop()
        sys.exit(1)

    server_connection = login_window.server_connection
    rally_config = login_window.get_rally_config()

    # NOW we are LOGGED IN!
    main_window = MainWindow(rally_config, server_connection, running_as_exe)
    main_window.run()
    login_window.stop()