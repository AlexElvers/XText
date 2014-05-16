"""
XText is a Python remake of the Gtk text widget named "xtext",  written  by
Peter Zelezny and used by XChat.


Copyright (c) 2014 Alexander Elvers

Permission is hereby granted, free of charge, to  any  person  obtaining  a
copy of this software and associated documentation files (the  "Software"),
to deal in the Software without restriction, including  without  limitation
the rights to use, copy, modify, merge,  publish,  distribute,  sublicense,
and/or sell copies of the Software, and  to  permit  persons  to  whom  the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included  in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS  OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE  WARRANTIES  OF  MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN  NO  EVENT  SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR  OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT,  TORT  OR  OTHERWISE,  ARISING
FROM, OUT OF OR IN CONNECTION  WITH  THE  SOFTWARE  OR  THE  USE  OR  OTHER
DEALINGS IN THE SOFTWARE.
"""
from gi.repository import Gtk, Gdk, Pango, PangoCairo
from contextlib import contextmanager
import cairo

__all__ = ["XText"]


def halfpx(*args):
    """
    Add 0.5 to each pixel.
    """
    return [x + .5 for x in args]

def color(*args):
    """
    Convert a color in 0x0000 .. 0xffff to 0.0 .. 1.0
    """
    return tuple(x / 0xffff for x in args)

@contextmanager
def saved(cr):
    """
    Context manager for cairo context save and restore.

    Returns the cairo context.

    The use of
    >>> with saved(cr):
    >>>     pass  # do something
    is equivalent to
    >>> cr.save()
    >>> try:
    >>>     pass  # do something
    >>> finally:
    >>>     cr.restore()
    """
    cr.save()
    try:
        yield cr
    finally:
        cr.restore()

def strip_attributes(text):
    """
    Remove attributes (bold, underline, color) from a text.
    """
    text = text.replace("\x02", "").replace("\x0F", "").replace("\x1F", "")
    parts = text.split("\x03")
    for p in range(len(parts[1:])):
        part = parts[p+1]
        if part[0:1] in "0123456789":
            part = part[1:]
            if part[0:1] in "0123456789":
                part = part[1:]
        if part[0:1] == "," and part[1:2] in "0123456789":
            part = part[2:]
            if part[0:1] in "0123456789":
                part = part[1:]
        parts[p+1] = part
    return "".join(parts)


class XText(Gtk.Misc):
    __gtype_name__ = 'XText'

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.set_size_request(200, 400)

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK)
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.connect("size-allocate", XText.size_allocate_cb)

        self.selection_active = False
        self.selection_start = None
        self.selection_end = None

        self.space_width = 16
        self.buffer = []
        self.buffer_indent = 50
        self.margin = 2
        self.sublines = []

        self.colors = {
            "background": color(0xf0f0, 0xf0f0, 0xf0f0),
            "foreground": color(0x2512, 0x29e8, 0x2b85),
            "mark_backg": color(0x2020, 0x4a4a, 0x8787),
            "mark_foreg": color(0xd3d3, 0xd7d7, 0xcfcf),
            "light_sep":  color(0xffff, 0xffff, 0xffff),
            "dark_sep":   color(0x1111, 0x1111, 0x1111),
            "thin_sep":   color(0x8e38, 0x8e38, 0x9f38),
            "text":       color(0x0000, 0x0000, 0x0000),
             0:           color(0xd3d3, 0xd7d7, 0xcfcf), # white
             1:           color(0x2e2e, 0x3434, 0x3636), # black
             2:           color(0x3434, 0x6565, 0xa4a4), # blue
             3:           color(0x4e4e, 0x9a9a, 0x0606), # green
             4:           color(0xcccc, 0x0000, 0x0000), # red
             5:           color(0x8f8f, 0x3939, 0x0202), # light red
             6:           color(0x5c5c, 0x3535, 0x6666), # purple
             7:           color(0xcece, 0x5c5c, 0x0000), # orange
             8:           color(0xc4c4, 0xa0a0, 0x0000), # yellow
             9:           color(0x7373, 0xd2d2, 0x1616), # green
            10:           color(0x1111, 0xa8a8, 0x7979), # aqua
            11:           color(0x5858, 0xa1a1, 0x9d9d), # light aqua
            12:           color(0x5757, 0x7979, 0x9e9e), # blue
            13:           color(0xa0d0, 0x42d4, 0x6562), # light purple
            14:           color(0x5555, 0x5757, 0x5353), # grey
            15:           color(0x8888, 0x8a8a, 0x8585), # light grey
        }

        self.fonts = {
            "normal": "Monospace 9",
            "bold": "Monospace Bold 9",
        }
        for font in self.fonts:
            self.fonts[font] = Pango.font_description_from_string(self.fonts[font])

        pcx = self.create_pango_context()
        metrics = pcx.get_metrics(self.fonts["normal"])
        self.ascent = metrics.get_ascent() // Pango.SCALE
        self.fontheight = (metrics.get_ascent() + metrics.get_descent()) // Pango.SCALE

    def break_line(self, line, max_width):
        """
        Break buffer lines into sublines if they are longer than the widget
        width.
        """
        bold = False
        fcolor = None
        bcolor = None
        underline = False
        startattrs = dict(bold=bold, fcolor=fcolor, bcolor=bcolor, underline=underline, first_subline=True)

        left = 0
        text = line
        i = -1
        while text:
            i += 1
            c, text = text[0], text[1:]
            if c == "\x02":
                bold = not bold
                continue
            if c == "\x03":
                fcolor = bcolor = None
                if len(text) > 0 and text[0] in "0123456789":
                    if len(text) > 1 and text[1] in "0123456789":
                        fcolor, text = int(text[0:2]), text[2:]
                        i += 2
                    else:
                        fcolor, text = int(text[0]), text[1:]
                        i += 1
                if len(text) > 1 and text[0] == "," and text[1] in "0123456789":
                    if len(text) > 2 and text[2] in "0123456789":
                        bcolor, text = int(text[1:3]), text[3:]
                        i += 3
                    else:
                        bcolor, text = int(text[1]), text[2:]
                        i += 2
                else:
                    bcolor = None
                continue
            if c == "\x0F":
                bold = underline = False
                fcolor = bcolor = None
                continue
            if c == "\x1F":
                underline = not underline
                continue

            layout = self.create_pango_layout(c)
            layout.set_font_description(self.fonts["normal"])
            width, height = layout.get_pixel_size()
            left += width

            if left > max_width:
                offset = 0
                for j in range(min(25, i)):
                    if line[i - j] == " ":
                        i -= j
                        offset = 1
                        break
                startattrs["offset"] = offset
                yield startattrs, line[:i]
                startattrs = dict(bold=bold, fcolor=fcolor, bcolor=bcolor, underline=underline, first_subline=False)
                text = line = line[i+offset:]
                left = 0
                i = -1

        startattrs["offset"] = 0
        yield startattrs, line

    def do_draw(self, cr):
        """
        Draw the widget graphics.
        """
        allocation = self.get_allocation()
        self.buffer_indent = max(self.buffer_indent, self.margin)

        # draw background
        self.set_source_color(cr, "background")
        cr.paint()

        # draw lines
        with saved(cr):
            for i, (attrs, subline) in enumerate(self.sublines):
                self.draw_line(cr, attrs, subline, i, self.fontheight * i)

        # self.draw_sep(cr)

    def draw_line(self, cr, attrs, text, subline_no, top=0):
        """
        Draw a subline.
        """
        bold = attrs["bold"]
        fcolor = attrs["fcolor"]
        bcolor = attrs["bcolor"]
        underline = attrs["underline"]

        if self.selection_start is not None and self.selection_end is not None:
            s_start, s_end = sorted([self.selection_start, self.selection_end])
        else:
            s_start = s_end = None

        left = 0
        i = -1
        while text:
            i += 1
            c, text = text[0], text[1:]
            if c == "\x02":
                bold = not bold
                continue
            if c == "\x03":
                fcolor = bcolor = None
                if len(text) > 0 and text[0] in "0123456789":
                    if len(text) > 1 and text[1] in "0123456789":
                        fcolor, text = int(text[0:2]), text[2:]
                        i += 2
                    else:
                        fcolor, text = int(text[0]), text[1:]
                        i += 1
                if len(text) > 1 and text[0] == "," and text[1] in "0123456789":
                    if len(text) > 2 and text[2] in "0123456789":
                        bcolor, text = int(text[1:3]), text[3:]
                        i += 3
                    else:
                        bcolor, text = int(text[1]), text[2:]
                        i += 2
                else:
                    bcolor = None
                continue
            if c == "\x0F":
                bold = underline = False
                fcolor = bcolor = None
                continue
            if c == "\x1F":
                underline = not underline
                continue

            layout = self.create_pango_layout(c)
            layout.set_font_description(self.fonts["bold" if bold else "normal"])
            width, height = layout.get_pixel_size()

            # draw background
            cr.rectangle(left, top, width, height)
            if s_start is not None and \
               s_start <= (subline_no, i) < s_end:
                self.set_source_color(cr, "mark_backg")
            elif bcolor is None:
                self.set_source_color(cr, "background")
            else:
                self.set_source_color(cr, bcolor % 16)
            cr.fill()

            # draw character
            if s_start is not None and \
               s_start <= (subline_no, i) < s_end:
                self.set_source_color(cr, "mark_foreg")
            elif fcolor is None:
                self.set_source_color(cr, "text")
            else:
                self.set_source_color(cr, fcolor % 16)
            cr.move_to(left, top)
            PangoCairo.show_layout(cr, layout)

            # draw underline
            if underline:
                with saved(cr):
                    cr.set_line_width(1)
                    cr.set_line_cap(cairo.LINE_CAP_SQUARE)
                    cr.move_to(*halfpx(left, top + self.ascent + 1))
                    cr.line_to(*halfpx(left + width, top + self.ascent + 1))
                    cr.stroke()

            left += width

    def draw_sep(self, cr):
        """
        Draw the separator line.

        (not used)
        """
        allocation = self.get_allocation()
        height = allocation.height

        self.set_source_color(cr, "thin_sep")
        cr.set_line_width(1)
        cr.move_to(*halfpx(x, 0))
        cr.line_to(*halfpx(x, height))
        cr.stroke()

    def set_source_color(self, cr, color_name):
        """
        Set the source color.
        """
        cr.set_source_rgba(*self.colors[color_name])

    def do_button_press_event(self, event):
        """
        Start selection.
        """
        subline = self.find_char_at_pos(event.x, event.y)
        if subline is not None:
            self.selection_active = True
            self.selection_start = subline[:2]
            self.selection_end = None
        else:
            self.selection_active = False
            self.selection_start = self.selection_end = None

    def do_button_release_event(self, event):
        """
        End selection.
        """
        if self.selection_active:
            self.selection_active = False
            subline = self.find_char_at_pos(event.x, event.y)
            if subline is not None:
                self.selection_end = subline[:2]

            if subline is None or self.selection_start == self.selection_end:
                self.selection_start = self.selection_end = None
            else:
                try:
                    self.clipboard.set_text(self.get_selection(), -1)
                except IndexError:
                    pass  # don't set clipboard text if lines out of range are selected
            self.queue_draw()

    def do_motion_notify_event(self, event):
        """
        Refresh the selection end.
        """
        if self.selection_active:
            subline = self.find_char_at_pos(event.x, event.y)
            if subline is not None:
                self.selection_end = subline[:2]
            self.queue_draw()

    def find_char_at_pos(self, x, y):
        """
        Find the subline number, the character  number  and  the  character
        itself at the given x/y-coordinates.

        If there is no character at the coordinates, the character text  is
        empty and the number is equal to the subline length.
        """
        left = 0
        try:
            subline_no, text = self.find_subline_at_pos(y)
        except TypeError:
            return None
        i = -1
        while text:
            i += 1
            c, text = text[0], text[1:]
            if c in ("\x02", "\x0F", "\x1F"):
                continue
            if c == "\x03":
                if len(text) > 0 and text[0] in "0123456789":
                    if len(text) > 1 and text[1] in "0123456789":
                        text = text[2:]
                        i += 2
                    else:
                        text = text[1:]
                        i += 1
                if len(text) > 1 and text[0] == "," and text[1] in "0123456789":
                    if len(text) > 2 and text[2] in "0123456789":
                        text = text[3:]
                        i += 3
                    else:
                        text = text[2:]
                        i += 2
                else:
                    bcolor = None
                continue

            layout = self.create_pango_layout(c)
            layout.set_font_description(self.fonts["normal"])
            width, height = layout.get_pixel_size()

            if left <= x < left + width:
                return subline_no, i, c

            left += width
        return subline_no, i + 1, ""

    def find_subline_at_pos(self, y):
        """
        Find the subline number and subline text at a given y-coordinate.

        If there is no subline at the y-coordinate,  the  subline  text  is
        empty.
        """
        subline_no = int(y / self.fontheight)
        if subline_no < len(self.sublines):
            return subline_no, self.sublines[subline_no][1]
        return subline_no, ""

    def get_selection(self):
        """
        Return the text between selection start and selection end.

        If end is smaller than start, start and end are swapped.  The start
        is included in the selected text, the end is excluded.
        """
        (sl, si), (el, ei) = sorted([self.selection_start, self.selection_end])
        sublines = self.sublines[sl:el+1]
        if not sublines:
            raise IndexError("selection out of range")
        if len(sublines) == 1:
            return sublines[0][1][si:ei]
        # more than one line
        text = sublines[0][1][si:] + " " * sublines[0][0]["offset"]  # first
        for subline in sublines[1:-1]:  # middle
            text += "\n" * subline[0]["first_subline"] + subline[1] + " " * subline[0]["offset"]
        text += "\n" * sublines[-1][0]["first_subline"] + sublines[-1][1][:ei]  # last
        return strip_attributes(text)

    def size_allocate_cb(self, rect):
        # break lines
        self.sublines = []
        for line in self.buffer:
            self.sublines += list(self.break_line(line, rect.width))
