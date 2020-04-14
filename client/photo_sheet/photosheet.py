import os
from tkinter import *
from tkinter.ttk import Combobox

from PIL import ImageTk,Image
import argparse

parser = argparse.ArgumentParser(description='Shows a photo sheet')
parser.add_argument("-p", "--port", type=int, help="UDP port of the main client", required=True)
parser.add_argument("-c", "--client_index", type=int, help="Client index, used in communication", required=True)
parser.add_argument("-u", "--user_id", type=int, help="User ID", required=True)
parser.add_argument("-i", "--index", type=int, help="Index of this photo sheet instance", required=True)

args = parser.parse_args()

window = Tk()
window.title("Photo Sheet {0}".format(args.index))

print(os.getcwd())
photos_img = ImageTk.PhotoImage(Image.open("test_data/photo_sheet_{0}.png".format(args.index)))
w = photos_img.width()
h = photos_img.height()
window.geometry('%dx%d+0+0' % (w, h))
background_label = Label(window, image=photos_img)
background_label.place(x=0, y=0, relwidth=1, relheight=1)

comboExample = Combobox(window,
                        values=["1-8",
                                "9-15",
                                "16-23",
                                "24-31",
                                "32-40"])
comboExample.place(x=0, y=0)
window.mainloop()
