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

import enum
import cairo
import math
import functools

from gi.repository import Gtk, Gdk, Pango, PangoCairo
from contextlib import contextmanager

__all__ = ["XText", "ScrollableXText", "FormatType", "Color", "ColorCode"]


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
    text = text.replace(FormatType.BOLD, "").replace(FormatType.RESET, "").replace(FormatType.UNDERLINE, "")
    parts = text.split(FormatType.COLOR)
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


class FormatType(str, enum.Enum):

    """
    The format codes for BOLD, COLOR, UNDERLINE and RESET

    Usage:
    >>> FormatType.BOLD + 'hello'
    '\\x02hello'
    """

    BOLD = "\x02"
    COLOR = "\x03"
    RESET = "\x0F"
    UNDERLINE = "\x1F"

    def __str__(self):
        return self.value


class ColorCode(enum.IntEnum):

    """
    The color codes

    Usage:
    >>> FormatType.COLOR + ColorCode.ORANGE
    '\\x0307'
    >>> Color(ColorCode.ORANGE)
    '\\x0307'
    """

    WHITE = 0
    BLACK = 1
    BLUE = 2
    GREEN = 3
    RED = 4
    LIGHT_RED = 5
    PURPLE = 6
    ORANGE = 7
    YELLOW = 8
    LIGHT_GREEN = 9
    AQUA = 10
    LIGHT_AQUA = 11
    LIGHT_BLUE = 12
    LIGHT_PURPLE = 13
    GREY = 14
    LIGHT_GREY = 15

    def __str__(self):
        return "%02d" % self

    def __add__(self, other):
        return "%02d%s" % (self, other)

    def __radd__(self, other):
        return "%s%02d" % (other, self)


class Color:

    """
    A color contains a foreground and a background part.

    Usage:
    >>> Color(ColorCode.RED) + "hello"
    '\\x0304hello'
    >>> Color(4) + "hello"
    '\\x0304hello'
    >>> Color(bg=ColorCode.RED) + "hello"
    '\\x03,04hello'
    >>> Color(ColorCode.RED, ColorCode.BLUE) + "hello"
    '\\x0304,02hello'
    >>> Color() + "hello"
    '\\x03hello'
    """

    def __init__(self, fg=None, bg=None):
        self.fg = fg
        self.bg = bg

    def __str__(self):
        t = FormatType.COLOR
        if self.fg is not None:
            t += "%02d" % self.fg
        if self.bg is not None:
            t += ",%02d" % self.bg
        return t

    def __add__(self, other):
        return "%s%s" % (self, other)

    def __radd__(self, other):
        return "%s%s" % (other, self)


class XText(Gtk.Misc):
    __gtype_name__ = 'XText'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK)
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.connect("size-allocate", XText.size_allocate_cb)

        self.selection_active = False
        self.selection_start = None
        self.selection_end = None

        self.buffer = []
        self.buffer_indent = 50
        self.margin = 2
        self.sublines = []
        self.start_subline = 0  # the first displayed subline
        self.start_offset = 0  # the offset of the first subline
        self.max_lines = 0.0  # maximal number of lines that fit into the widget height (float)

        self.colors = {
            "background":           color(0xf0f0, 0xf0f0, 0xf0f0),
            "foreground":           color(0x2512, 0x29e8, 0x2b85),
            "mark_backg":           color(0x2020, 0x4a4a, 0x8787),
            "mark_foreg":           color(0xd3d3, 0xd7d7, 0xcfcf),
            "light_sep":            color(0xffff, 0xffff, 0xffff),
            "dark_sep":             color(0x1111, 0x1111, 0x1111),
            "thin_sep":             color(0x8e38, 0x8e38, 0x9f38),
            "text":                 color(0x0000, 0x0000, 0x0000),
            ColorCode.WHITE:        color(0xd3d3, 0xd7d7, 0xcfcf),
            ColorCode.BLACK:        color(0x2e2e, 0x3434, 0x3636),
            ColorCode.BLUE:         color(0x3434, 0x6565, 0xa4a4),
            ColorCode.GREEN:        color(0x4e4e, 0x9a9a, 0x0606),
            ColorCode.RED:          color(0xcccc, 0x0000, 0x0000),
            ColorCode.LIGHT_RED:    color(0x8f8f, 0x3939, 0x0202),
            ColorCode.PURPLE:       color(0x5c5c, 0x3535, 0x6666),
            ColorCode.ORANGE:       color(0xcece, 0x5c5c, 0x0000),
            ColorCode.YELLOW:       color(0xc4c4, 0xa0a0, 0x0000),
            ColorCode.LIGHT_GREEN:  color(0x7373, 0xd2d2, 0x1616),
            ColorCode.AQUA:         color(0x1111, 0xa8a8, 0x7979),
            ColorCode.LIGHT_AQUA:   color(0x5858, 0xa1a1, 0x9d9d),
            ColorCode.LIGHT_BLUE:   color(0x5757, 0x7979, 0x9e9e),
            ColorCode.LIGHT_PURPLE: color(0xa0d0, 0x42d4, 0x6562),
            ColorCode.GREY:         color(0x5555, 0x5757, 0x5353),
            ColorCode.LIGHT_GREY:   color(0x8888, 0x8a8a, 0x8585),
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

    @functools.lru_cache(maxsize=128)
    def get_pango_layout(self, char, bold):
        layout = self.create_pango_layout(char)
        layout.set_font_description(self.fonts["bold" if bold else "normal"])
        return layout, layout.get_pixel_size()

    def redraw(self):
        self.size_allocate_cb(self.get_allocation())
        self.queue_draw()

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
            if c == FormatType.BOLD:
                bold = not bold
                continue
            if c == FormatType.COLOR:
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
            if c == FormatType.RESET:
                bold = underline = False
                fcolor = bcolor = None
                continue
            if c == FormatType.UNDERLINE:
                underline = not underline
                continue

            layout, (width, height) = self.get_pango_layout(c, bold)
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
        self.buffer_indent = max(self.buffer_indent, self.margin)

        # draw background
        self.set_source_color(cr, "background")
        cr.paint()

        # draw lines
        with saved(cr):
            for i, (attrs, subline) in enumerate(self.sublines[self.start_subline:self.start_subline + int(self.max_lines + 1)]):
                self.draw_line(cr, attrs, subline, i + self.start_subline, self.fontheight * i - self.start_offset)

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
            if c == FormatType.BOLD:
                bold = not bold
                continue
            if c == FormatType.COLOR:
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
            if c == FormatType.RESET:
                bold = underline = False
                fcolor = bcolor = None
                continue
            if c == FormatType.UNDERLINE:
                underline = not underline
                continue

            layout, (width, height) = self.get_pango_layout(c, bold)

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

    def draw_sep(self, cr, x):
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
            if c in (FormatType.BOLD, FormatType.RESET, FormatType.UNDERLINE):
                continue
            if c == FormatType.COLOR:
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
                continue

            layout, (width, height) = self.get_pango_layout(c, False)

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
        if el >= len(self.sublines):
            text += "\n" * sublines[-1][0]["first_subline"] + sublines[-1][1]  # last, full line
        else:
            text += "\n" * sublines[-1][0]["first_subline"] + sublines[-1][1][:ei]  # last, end contained
        return strip_attributes(text)

    def size_allocate_cb(self, rect):
        self.max_lines = self.get_allocation().height / self.fontheight

        # save selection
        if self.selection_start is not None:
            (sl, si), (el, ei) = self.selection_start, self.selection_end
            sc = si
            ec = ei
            for i, line in enumerate(self.sublines):
                if i < sl:
                    sc += len(line[1]) + line[0]["offset"]
                if i < el:
                    ec += len(line[1]) + line[0]["offset"]
                elif i >= sl:
                    break

        # break lines
        self.sublines = []
        for line in self.buffer:
            self.sublines += list(self.break_line(line, rect.width))

        # restore selection
        if self.selection_start is not None:
            sl = el = 0
            for i, line in enumerate(self.sublines):
                if sc != -1:
                    if sc < len(line[1]) + line[0]["offset"]:
                        sl = i
                        si = sc
                        sc = -1
                    else:
                        sc -= len(line[1]) + line[0]["offset"]
                if ec != -1:
                    if ec < len(line[1]) + line[0]["offset"]:
                        el = i
                        ei = ec
                        ec = -1
                    else:
                        ec -= len(line[1]) + line[0]["offset"]
                if sc == ec == -1:
                    break
            else:
                # start or end after last character
                if sc != -1:
                    sl = i + 1
                    si = 0
                if ec != -1:
                    el = i + 1
                    ei = 0
            self.selection_start, self.selection_end = (sl, si), (el, ei)


class ScrollableXText(Gtk.Box):
    __gtype_name__ = 'ScrollableXText'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.adjustment = Gtk.Adjustment(value=0.0,
                                         lower=0.0,
                                         upper=1.0,
                                         step_increment=0.05,
                                         page_increment=0.05,
                                         page_size=0.05)
        self.adjustment.connect("value-changed", self.value_changed_cb)

        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.xtext = XText()
        self.scrollbar = Gtk.Scrollbar(orientation=Gtk.Orientation.VERTICAL,
                                       adjustment=self.adjustment)

        self.pack_start(self.xtext, True, True, 0)
        self.pack_start(self.scrollbar, False, True, 0)

        self.xtext.add_events(Gdk.EventMask.SCROLL_MASK)
        self.xtext.connect("scroll-event", self.scroll_cb)
        self.xtext.connect("size-allocate", self.size_allocate_cb)

    def value_changed_cb(self, adjustment):
        numsublines = len(self.xtext.sublines)
        maxlines = self.xtext.max_lines
        if numsublines >= maxlines:
            x = math.modf(adjustment.get_value() * (numsublines - maxlines))
            self.xtext.start_subline = int(x[1])
            self.xtext.start_offset = int(self.xtext.fontheight * x[0])
            self.xtext.queue_draw()

    def size_allocate_cb(self, widget, allocation):
        self.adjustment.value_changed()

    def scroll_cb(self, widget, event):
        if event.direction == Gdk.ScrollDirection.UP:
            self.adjustment.set_value(max(self.adjustment.get_value() - 1 / (len(self.xtext.sublines) - self.xtext.max_lines), 0))
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.adjustment.set_value(min(self.adjustment.get_value() + 1 / (len(self.xtext.sublines) - self.xtext.max_lines), 1))
