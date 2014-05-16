# XText

XText is a Python 3 remake of the GTK+ 2 text widget named "xtext",  written  by
Peter Zelezny and used by XChat.

## Requirements

XText is a GTK+ 3 widget, so it uses `Gtk`, `Gdk`, `Pango` and `PangoCairo` from `gi.repository` and `cairo`.

## Current features

- text attributes _bold_, _underline_ and _font colors_ (foreground and background) like in XChat or mIRC:
    - _bold_ is `\x02` (the ASCII character)
    - _underline_ is `\x1F`
    - _color_ is `\x03`
        - `\x034` and `\x0304` mean foreground color 04 (red)
        - `\x03,4` and `\x03,04` mean background color 04 (red)
        - `\x034,4`, `\x034,04`, `\x0304,4` and `\x0304,04` mean foreground and background color 04 (red)
    - reset of all attributes with `\x0F` (single attributes can be reset with the special character again)
- word wrap
- selection of text with automatic copy to clipboard

## To do

- indentation of text with a movable separator line
- update selection on resize
- URL detection with a user-defined click handler

## License

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
