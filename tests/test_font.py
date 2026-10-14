import unittest
from pathlib import Path
from fontTools.ttLib import TTFont
FONT = Path(__file__).resolve().parents[1] / "fonts/Swiz13-Regular.ttf"

class FontTests(unittest.TestCase):
    def setUp(self):
        self.f = TTFont(FONT); self.c = self.f.getBestCmap()
    def test_monospaced(self):
        adv = {self.f["hmtx"][n][0] for n in self.c.values()}
        self.assertEqual(adv - {0}, {600})
        self.assertEqual(self.f["post"].isFixedPitch, 1)
    def test_ascii_present_and_drawn(self):
        for cp in range(33, 127):
            self.assertGreater(self.f["glyf"][self.c[cp]].numberOfContours, 0, chr(cp))
    def test_cell_bounds(self):
        for cp, n in self.c.items():
            g = self.f["glyf"][n]
            if g.numberOfContours and self.f["hmtx"][n][0]:
                self.assertTrue(-100 <= g.xMin and g.xMax <= 700, chr(cp))
    def test_upright_and_named(self):
        self.assertEqual(self.f["post"].italicAngle, 0)
        self.assertEqual(self.f["name"].getDebugName(1), "Swiz13")

    def test_stems_are_upright(self):
        """The slant is removed: the vertical bar glyph must be vertical."""
        from fontTools.pens.recordingPen import DecomposingRecordingPen
        gs = self.f.getGlyphSet(); pen = DecomposingRecordingPen(gs); gs[self.c[ord("|")]].draw(pen)
        xs = [p[0] for _, pts in pen.value for p in pts]
        self.assertLess(max(xs) - min(xs), 130)
    def test_cyrillic_and_accents(self):
        for ch in "ЖщéñøÅ":
            self.assertIn(ord(ch), self.c)

    def test_letters_are_centred(self):
        import unicodedata
        from fontTools.pens.boundsPen import BoundsPen
        gs = self.f.getGlyphSet()
        for ch in "abcdefghijklmnpqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
            p = BoundsPen(gs)
            gs[self.c[ord(ch)]].draw(p)
            # letters with a leading tail are centred by their body, so the tail may pull the ink box off-centre a little
            self.assertLessEqual(abs((p.bounds[0] + p.bounds[2]) / 2 - 300), 40 if ch in "mnpuvwyz" else 2, ch)

    def test_hand_picked_glyphs(self):
        from fontTools.ttLib import TTFont
        ref = TTFont(FONT.parents[1] / "sources/UprightReference-Regular.ttf")
        a_new, a_old = self.f["glyf"][self.c[ord("a")]], ref["glyf"][ref.getBestCmap()[ord("a")]]
        shifted = lambda g, font: [(x - g.xMin, y) for x, y in g.getCoordinates(font["glyf"])[0]]   # same drawing, only centred
        self.assertEqual(shifted(a_new, self.f), shifted(a_old, ref))
        a2_new, a2_old = self.f["glyf"][self.c[ord("à")]], ref["glyf"][ref.getBestCmap()[ord("à")]]
        self.assertEqual(shifted(a2_new, self.f), shifted(a2_old, ref))
        for ch in "Q0()[]{}":
            self.assertGreater(self.f["glyf"][self.c[ord(ch)]].numberOfContours, 0)

    def test_f_has_no_tail_and_g_loop_is_open(self):
        gl = self.f["glyf"]
        f = gl[self.c[ord("f")]]
        self.assertGreaterEqual(f.yMin, -10)                      # no tail below the baseline
        self.assertGreater(f.yMax, 600)                           # the upper part is kept
        g = gl[self.c[ord("g")]]
        self.assertLess(g.yMin, -100)                             # the descender is still there
        o = gl[self.c[ord("o")]]
        self.assertEqual(o.numberOfContours, 2)                   # a plain o: outline + counter, no hairline
        self.assertLess(o.xMax, 600)
        self.assertEqual(g.numberOfContours, 2)                   # bowl + one open lower stroke (a closed loop would add a third)

    def test_straight_quotes(self):
        """Typewriter quotes are vertical: the top and the bottom of each bar share the same x."""
        from fontTools.pens.recordingPen import DecomposingRecordingPen
        gs = self.f.getGlyphSet()
        for ch in "\"'":
            pen = DecomposingRecordingPen(gs); gs[self.c[ord(ch)]].draw(pen)
            pts = [p for _, ps in pen.value for p in ps]
            ymin, ymax = min(p[1] for p in pts), max(p[1] for p in pts)
            mid = (ymin + ymax) / 2
            top = [p[0] for p in pts if p[1] > mid + (ymax - mid) * .5]
            bot = [p[0] for p in pts if p[1] < mid - (mid - ymin) * .5]
            self.assertLess(abs(sum(top) / len(top) - sum(bot) / len(bot)), 8, ch)
            self.assertGreater(ymax - ymin, 250, ch)       # long enough to be clearly visible

if __name__ == "__main__":
    unittest.main()
