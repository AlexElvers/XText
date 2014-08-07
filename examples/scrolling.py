#!/usr/bin/env python3

import sys
sys.path.append("..")

from gi.repository import Gtk
from xtext import ScrollableXText

xtext = ScrollableXText()
xtext.xtext.set_size_request(400, 200)
xtext.xtext.buffer = [
    4 * ("Hello World %2d!" % x) for x in range(100)
]

window = Gtk.Window(title="GtkXText")
window.connect("destroy", Gtk.main_quit)
window.add(xtext)
window.show_all()
Gtk.main()
