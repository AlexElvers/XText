#!/usr/bin/env python3

import sys
sys.path.append("..")

from gi.repository import Gtk
from xtext import XText


xtext = XText()
xtext.set_size_request(200, 400)
xtext.buffer = [
    "Hello World!",
    "Hello World!UnderlineResetUnderlineReset",
    "04ColorResetBold04Bold&colorUnbold&colorBold&colorReset",
    "00White03Green04Red7Orange08YellowNone",
    ",00White,03Green,04Red,7Orange,08YellowNone",
    "00,00White03,3Green4,04Red7,7Orange8,08YellowNone",
    "AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA AAAAA",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa bbbbbcccccbbbbbcccccbb24",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa bbbbbcccccbbbbbcccccbbb25",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa bbbbbcccccbbbbbcccccbbbb26",
]

window = Gtk.Window(title="GtkXText")
window.connect("destroy", Gtk.main_quit)
window.add(xtext)
window.show_all()
Gtk.main()
