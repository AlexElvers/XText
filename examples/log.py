#!/usr/bin/env python3

import sys
sys.path.append("..")

import time
from gi.repository import Gtk, GObject
from xtext import XText


class XLogger(XText):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_line(self, timestamp, message):
        self.buffer.append("15[%s] %s" % (time.strftime("%T", time.localtime(timestamp)), message))
        self.redraw()


lines = [
    "Hey!",
    "What's up?",
    "Every second, a line was added."
]

def add():
    xlogger.add_line(time.time(), lines.pop(0))
    return bool(lines)


xlogger = XLogger()
xlogger.set_size_request(600, 400)

window = Gtk.Window(title="GtkXText")
window.connect("destroy", Gtk.main_quit)
window.add(xlogger)
window.show_all()

GObject.timeout_add(1000, add)

Gtk.main()
