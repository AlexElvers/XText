import unittest
import xtext


class HelperTest(unittest.TestCase):
    def test_strip_attributes(self):
        sa = xtext.strip_attributes

        self.assertEqual(sa("Hello World"), "Hello World")
        self.assertEqual(sa("\x02Hello \x0FWorld\x1F"), "Hello World")
        self.assertEqual(sa("Hello\x03 World\x03 Hello"), "Hello World Hello")
        self.assertEqual(sa("Hello\x030 World\x03,1 Hello"), "Hello World Hello")
        self.assertEqual(sa("Hello\x030,1 World\x0300 Hello"), "Hello World Hello")
        self.assertEqual(sa("Hello\x03,11 World\x0300,11 Hello"), "Hello World Hello")
        self.assertEqual(sa("Hello\x03, World\x030011 Hello"), "Hello, World11 Hello")
        self.assertEqual(sa("\x0304Hello\x03,02 World\x031,1"), "Hello World")
        self.assertEqual(sa("\x0304\x03,02\x031,1"), "")


class SelectionTest(unittest.TestCase):
    def setUp(self):
        self.xtext = xtext.XText()

    def test_find_char(self):
        xtext = self.xtext
        height = xtext.fontheight

        layout = xtext.create_pango_layout("a")
        layout.set_font_description(xtext.fonts["normal"])
        a_width = layout.get_pixel_size()[0]
        layout = xtext.create_pango_layout("b")
        layout.set_font_description(xtext.fonts["normal"])
        b_width = layout.get_pixel_size()[0]
        layout = xtext.create_pango_layout("c")
        layout.set_font_description(xtext.fonts["normal"])
        c_width = layout.get_pixel_size()[0]

        xtext.sublines = [
            ({}, "abbc"),
        ]
        self.assertEqual((0, "abbc"), xtext.find_subline_at_pos(height / 2))
        self.assertEqual((0, 0, "a"), xtext.find_char_at_pos(a_width / 2, height / 2))
        self.assertEqual((0, "abbc"), xtext.find_subline_at_pos(height - 1))
        self.assertEqual((1, ""), xtext.find_subline_at_pos(height + 1))
        self.assertEqual((0, 0, "a"), xtext.find_char_at_pos(1, height / 2))
        self.assertEqual((0, 0, "a"), xtext.find_char_at_pos(a_width - 1, height / 2))
        self.assertEqual((0, 1, "b"), xtext.find_char_at_pos(a_width + 1, height / 2))
        self.assertEqual((0, 3, "c"), xtext.find_char_at_pos(a_width + 2 * b_width + c_width - 1, height / 2))
        self.assertEqual((0, 4, ""), xtext.find_char_at_pos(a_width + 2 * b_width + c_width + 1, height / 2))


        xtext.sublines = [
            ({}, "abbb"),
            ({}, "ccca"),
        ]
        self.assertEqual((1, "ccca"), xtext.find_subline_at_pos(height * 1.5))
        self.assertEqual((1, 3, "a"), xtext.find_char_at_pos(3 * c_width + 1, height * 1.5))
        self.assertEqual((2, 0, ""), xtext.find_char_at_pos(3 * c_width + 1, height * 2.5))


if __name__ == '__main__':
    unittest.main()
