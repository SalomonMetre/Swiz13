"""Finish the blended outlines with a typewriter touch and assemble Swiz13-Regular.ttf / .woff2."""
import hashlib, json, pickle, sys, unicodedata
from math import sin, cos, pi
from pathlib import Path

from fontTools.agl import UV2AGL
from fontTools.fontBuilder import FontBuilder
from fontTools.ttLib.tables.O_S_2f_2 import Panose
from fontTools.pens.ttGlyphPen import TTGlyphPen
from shapely import wkb
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient
from shapely import affinity
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
from donors import ROOT, Donor, SLANT

VERSION = "1.0"
DESLANT = True   # the donors' italic slant is sheared back out, so the letters stand upright
PITCH = 600
INK = 6.0        # ink spread: corners rounded by this radius
WOBBLE = 4.2     # amplitude of the uneven strike, in font units
STRIKE = 5       # each struck letter sits a little off its true position (units)
TILT = .7        # ... and a little off true vertical (degrees)


def glyph_name(cp):
    if cp in UV2AGL:
        return UV2AGL[cp]
    return f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:X}"


def typewriter(shape, cp, strike=True):
    """Ink spread plus a slightly uneven strike, deterministic per glyph."""
    if shape.is_empty:
        return shape
    # ink spreading into the paper: soften every corner
    shape = shape.buffer(-INK, 12).buffer(INK, 12)
    shape = shape.buffer(INK * .6, 12).buffer(-INK * .6, 12)
    seed = int(hashlib.md5(str(cp).encode()).hexdigest()[:8], 16)
    p1, p2, p3 = [(seed >> (8 * i) & 255) / 255 * 2 * pi for i in range(3)]

    def jitter(x, y):
        return (x + WOBBLE * (.5 * sin(x * .045 + y * .021 + p1) + .3 * sin(y * .071 - x * .017 + p2)
                              + .25 * sin(y * .13 + x * .09 + p3)),
                y + WOBBLE * (.5 * sin(y * .043 - x * .026 + p3) + .3 * sin(x * .067 + y * .019 + p1)
                              + .25 * sin(x * .12 - y * .08 + p2)))

    def ring(coords):
        seg = Polygon(coords).segmentize(14)
        return [jitter(x, y) for x, y in list(seg.exterior.coords)[:-1]]

    polys = [shape] if shape.geom_type == "Polygon" else list(shape.geoms)
    out = []
    for p in polys:
        q = Polygon(ring(p.exterior.coords), [ring(h.coords) for h in p.interiors])
        out.append(q if q.is_valid else q.buffer(0))
    result = unary_union(out)
    if strike:                       # a typewriter never lands a letter exactly square
        r = lambda i, a: ((seed >> (3 * i) & 15) / 7.5 - 1) * a
        result = affinity.rotate(result, r(1, TILT), origin=(300, 275))
        result = affinity.translate(result, r(2, STRIKE), r(3, STRIKE * .8))
    return result.simplify(.5, preserve_topology=True)


def deslant(shape):
    """Undo the italic slant about the middle of the x-height; all other shape features are kept."""
    from math import radians, tan
    t = tan(radians(SLANT))
    return affinity.affine_transform(shape, [1, -t, 0, 1, t * 275, 0])


UPRIGHT_REFERENCE = ROOT / "sources" / "UprightReference-Regular.ttf"   # upright drawing of the same style (source of the a)


_UPRIGHT = None


def is_latin_a(cp):
    """a and every precomposed a with accents (à á â ã ä å ā ă ą ǎ ǻ ...)."""
    return unicodedata.normalize("NFD", chr(cp))[0] == "a" and cp != ord("\u0430")


def upright_glyph(cp):
    """The finished outline of one character from the upright reference font, copied as is (None if it lacks it)."""
    global _UPRIGHT
    from fontTools.ttLib import TTFont
    if _UPRIGHT is None:
        _UPRIGHT = TTFont(UPRIGHT_REFERENCE)
    name = _UPRIGHT.getBestCmap().get(cp)
    if name is None:
        return None
    pen = TTGlyphPen(None)
    _UPRIGHT.getGlyphSet()[name].draw(pen)
    return pen.glyph()


def exact_glyph(fname, cp, scale=.5):
    """A donor glyph copied exactly, curves and all (only scaled to this font's 1000 units): no flattening, no finish."""
    from fontTools.ttLib import TTFont
    from fontTools.pens.transformPen import TransformPen
    font = TTFont(ROOT / "sources" / fname)
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    pen = TTGlyphPen(None)
    rec = DecomposingRecordingPen(font.getGlyphSet())                 # a donor glyph may be built from components
    font.getGlyphSet()[font.getBestCmap()[cp]].draw(rec)
    rec.replay(TransformPen(pen, (scale, 0, 0, scale, 0, 0)))
    return pen.glyph()


EXACT = {ord("~"): "GoogleSansCode-Regular.ttf", 0x2DC: "GoogleSansCode-Regular.ttf", 0x303: "GoogleSansCode-Regular.ttf"}      # copied from Google Sans Code as drawn


_GSC = None


def tilde_letter(cp, base_glyph):
    """A letter with a tilde (ã ñ õ ũ ẽ ỹ ...): this font's own base letter plus Google Sans Code's tilde, copied exactly
    from its ñ (or Ñ for capitals), moved to sit over the base letter."""
    global _GSC
    from fontTools.ttLib import TTFont
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.transformPen import TransformPen
    if _GSC is None:
        _GSC = TTFont(ROOT / "sources" / "GoogleSansCode-Regular.ttf")
    gs, cmap = _GSC.getGlyphSet(), _GSC.getBestCmap()
    upper = chr(cp).isupper()
    ref = cmap[ord("Ñ" if upper else "ñ")]
    base_ref = cmap[ord("N" if upper else "n")]
    bp = BoundsPen(gs)
    gs[base_ref].draw(bp)
    bx0, by0, bx1, by1 = bp.bounds
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    rec = DecomposingRecordingPen(gs)
    gs[ref].draw(rec)
    contours, cur = [], []
    for op, args in rec.value:
        cur.append((op, args))
        if op in ("closePath", "endPath"):
            contours.append(cur)
            cur = []
    accent = []
    for c in contours:
        pts = [pt for _, a in c for pt in a]
        if min(y for _, y in pts) > by1 + 10:                 # the pieces that float above the letter: the tilde
            accent.append(c)
    base_glyph.recalcBounds(None)
    bg_top = base_glyph.yMax
    dx = 300 - (bx0 + bx1) / 4                                # its centre onto the cell's centre
    dy = bg_top - by1 / 2
    pen = TTGlyphPen(None)
    base_glyph.draw(pen, None)
    tp = TransformPen(pen, (.5, 0, 0, .5, dx, dy))
    for c in accent:
        for op, args in c:
            getattr(tp, op)(*args)
    return pen.glyph()


TILDE_BASE = {"ĩ": "ı"}       # the dotted i takes a dotless base


def to_glyph(shape):
    pen = TTGlyphPen(None)
    polys = [] if shape.is_empty else ([shape] if shape.geom_type == "Polygon" else list(shape.geoms))
    for poly in polys:
        if poly.geom_type != "Polygon":
            continue
        poly = orient(poly, sign=-1.0)
        for ring in [poly.exterior, *poly.interiors]:
            pts = []
            for x, y in list(ring.coords)[:-1]:
                q = (round(x), round(y))
                if not pts or q != pts[-1]:
                    pts.append(q)
            if len(pts) > 2 and pts[0] == pts[-1]:
                pts.pop()
            if len(pts) < 3:
                continue
            pen.moveTo(pts[0])
            for q in pts[1:]:
                pen.lineTo(q)
            pen.closePath()
    return pen.glyph()


W_NARROW = .92       # w is narrowed by this factor so its tails fit inside the cell
FLAG_BASES = {"m": "left", "n": "left", "p": "left", "u": "left", "y": "left", "v": "both", "w": "both", "z": "zee"}
FLAG_LEN, FLAG_DROP, FLAG_ROOT, FLAG_TIP = 84, 54, 58, 30      # the tiny leading tail: length, drop, thickness at root and tip


def flag_sides(cp):
    """Which sides of this letter get a leading tail: lowercase m n p u y (left), v w z (both sides) and their accented forms."""
    base = unicodedata.normalize("NFD", chr(cp))[0]
    if not (chr(cp).islower() and base in FLAG_BASES and ord(base) < 0x80):
        return None
    return FLAG_BASES[base]


Z_TAIL = 52, 50, 28      # the z's tails: length, thickness at the bar, thickness at the tip


def add_z_tails(shape, cp):
    """The z: a small leading tail pointing down from the left end of the top bar, and a small ending tail pointing up
    from the right end of the bottom bar."""
    from shapely.geometry import Point
    length, root, tip = Z_TAIL
    xmin, ymin, xmax, ymax = shape.bounds
    top = shape.intersection(box(-100, 480, 700, 700)).bounds[3]
    left = shape.intersection(box(-100, top - 45, 700, top - 35)).bounds[0]
    right = shape.intersection(box(-100, ymin + 35, 700, ymin + 45)).bounds[2]
    parts = [shape]
    for x0, y0, d in ((left + root / 2 - 2, top - 38, -1), (right - root / 2 + 2, ymin + 40, 1)):
        discs = []
        for k in range(21):
            t = k / 20
            r = (root + (tip - root) * t) / 2
            discs.append(Point(x0 - d * 6 * t, y0 + d * (42 + length) * t).buffer(r, 12))
        parts.append(typewriter(unary_union(discs), cp + 7000, strike=False))
    return unary_union(parts).buffer(-2, 12).buffer(2, 12)


def add_flags(shape, cp, sides, dx=0):
    """A tiny leading tail on the letter's outer edge, like a typewriter-script entry stroke: it starts inside the stem
    and slopes down and away.  At the top-left (and for 'both', top-right)."""
    from shapely.geometry import Point
    if sides == "zee":
        return add_z_tails(shape, cp)
    band = shape.intersection(box(-100, 480, 700, 700))
    if band.is_empty:
        return shape
    top = band.bounds[3]
    ymin = shape.bounds[1]
    out = [shape]
    for side in (("left", "right") if sides == "both" else ("left",)):
        cy = top - FLAG_ROOT / 2
        probe = shape.intersection(box(-100, top - 40, 700, top - 30))
        if probe.is_empty:
            continue
        b = probe.bounds
        x, d = (b[0], -1) if side == "left" else (b[2], 1)
        room = (x + dx - 8) if side == "left" else (592 - x - dx)       # keep the tip inside the cell, clear of the next letter
        flen = max(14, min(FLAG_LEN, room - FLAG_TIP / 2))
        n = 24
        discs = []
        for k in range(n + 1):
            t = k / n
            r = (FLAG_ROOT + (FLAG_TIP - FLAG_ROOT) * t) / 2
            discs.append(Point(x - d * 16 + d * flen * t, cy - FLAG_DROP * t ** 1.4).buffer(r, 12))
        out.append(typewriter(unary_union(discs), cp + 7000, strike=False))
    return unary_union(out).buffer(-2, 12).buffer(2, 12)


def main():
    data = pickle.load(open(ROOT / "build" / "blend.pkl", "rb"))
    donors = {k: Donor(k) for k in ("maple", "hack", "martian")}
    order = sorted(data)
    names = [".notdef"] + [glyph_name(cp) for cp in order]
    glyphs = {".notdef": to_glyph(Polygon([(60, 0), (60, 730), (540, 730), (540, 0)],
                                         [[(120, 60), (480, 60), (480, 670), (120, 670)]]))}
    advances = {".notdef": PITCH}
    cmap = {}
    provenance = {}
    # pass 1: finish every outline
    finals, useds, bodies = {}, {}, {}
    for cp in order:
        wk, _, used = data[cp]
        shape = wkb.loads(wk) if wk else Polygon()
        combining = unicodedata.combining(chr(cp)) > 0
        if not shape.is_empty and any("clean" in k for k in used):
            pass                                  # drawn clean (the tilde): the donor outline as it is, no ink spread or wobble
        elif not shape.is_empty:
            shape = typewriter(shape, cp, strike=not combining and not any("straight" in k for k in used))
            if DESLANT and not any(k.endswith("-upright") for k in used):
                shape = deslant(shape).simplify(.5, preserve_topology=True)
        bodies[cp] = shape                       # the letter without its tails: centring goes by this
        sides = flag_sides(cp)
        if sides and not shape.is_empty:
            c = (shape.bounds[0] + shape.bounds[2]) / 2
            if unicodedata.normalize("NFD", chr(cp))[0] == "w":       # w fills its cell: narrow it a little to make room for the tails
                shape = affinity.scale(shape, W_NARROW, 1, origin=(c, 0))
                bodies[cp] = shape
            shape = add_flags(shape, cp, sides, 300 - c)
        finals[cp], useds[cp] = shape, used

    # pass 2: centre every letter in its cell (the ink's left and right extremes equidistant from the cell edges); an
    # accented letter takes its base letter's shift so accents stay where they belong.  The o is left alone: its ring
    # is already centred.
    def ink_centre(cp):
        if is_latin_a(cp) and upright_glyph(cp) is not None:
            g = upright_glyph(cp)
            g.recalcBounds(None)
            return (g.xMin + g.xMax) / 2 if g.numberOfContours else None
        b = bodies[cp].bounds if not bodies[cp].is_empty else None
        return (b[0] + b[2]) / 2 if b else None

    def is_letter(cp):
        return unicodedata.category(chr(cp)).startswith("L") and unicodedata.combining(chr(cp)) == 0

    def shift_for(cp):
        if not is_letter(cp):
            return 0
        base = ord(unicodedata.normalize("NFD", chr(cp))[0])
        src = base if base in finals and base != cp and is_letter(base) and base != ord("o") else cp
        if src == ord("o"):
            return 0
        c = ink_centre(src)
        return 0 if c is None else PITCH / 2 - c

    for cp in order:
        name = glyph_name(cp)
        used = useds[cp]
        combining = unicodedata.combining(chr(cp)) > 0
        advances[name] = 0 if combining else PITCH
        dx = shift_for(cp)
        glyphs[name] = to_glyph(affinity.translate(finals[cp], dx, 0) if dx else finals[cp])
        nfd = unicodedata.normalize("NFD", chr(cp))
        if "\u0303" in nfd[1:2] and len(nfd) == 2 and cp not in EXACT:
            base = TILDE_BASE.get(chr(cp).lower(), nfd[0])
            base = base.upper() if chr(cp).isupper() else base
            bname = cmap.get(ord(base))
            if bname in glyphs:
                glyphs[name] = tilde_letter(cp, glyphs[bname])
                used = {"google-sans-code-tilde": 1.0}
        if cp in EXACT:
            glyphs[name] = exact_glyph(EXACT[cp], cp)
            used = {"google-sans-code-exact": 1.0}
        if is_latin_a(cp) and upright_glyph(cp) is not None:      # the upright reference's a and its accented forms
            g = upright_glyph(cp)
            if dx and g.numberOfContours:
                g.coordinates.translate((round(dx), 0))
            glyphs[name] = g
            used = {"upright-reference": 1.0}
        cmap[cp] = name
        provenance[f"U+{cp:04X}"] = {"glyph": name, "blend": {k: round(v, 2) for k, v in used.items()}}

    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    metrics = {}
    for n in names:
        g = fb.font["glyf"][n]
        g.recalcBounds(fb.font["glyf"])
        metrics[n] = (advances[n], getattr(g, "xMin", 0) if g.numberOfContours else 0)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=1000, descent=-300, lineGap=0)
    fb.setupNameTable({
        "familyName": "Swiz13", "styleName": "Regular",
        "uniqueFontIdentifier": f"Swiz13-Regular-{VERSION}", "fullName": "Swiz13 Regular",
        "psName": "Swiz13-Regular", "version": f"Version {VERSION}",
        "copyright": "Swiz13 is a blend of Martian Mono, Maple Mono, Hack and Google Sans Code. Martian Mono (c) Evil Martians, "
                     "Maple Mono and Google Sans Code (c) their Project Authors, Hack (c) Source Foundry Authors / Bitstream Vera.",
        "licenseDescription": "This Font Software is licensed under the SIL Open Font License 1.1 (Martian Mono, Maple Mono) "
                              "and the MIT / Bitstream Vera licenses (Hack). See licenses/.",
        "licenseInfoURL": "https://openfontlicense.org",
    })
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, sTypoLineGap=200, usWinAscent=1100, usWinDescent=330,
                sxHeight=550, sCapHeight=730, usWeightClass=400, usWidthClass=5, xAvgCharWidth=PITCH,
                fsSelection=0x40, achVendID="SMNK", fsType=0,
                panose=Panose(bFamilyType=2, bSerifStyle=0, bWeight=5, bProportion=9, bContrast=0, bStrokeVariation=0, bArmStyle=0, bLetterForm=0, bMidline=0, bXHeight=0))
    os2 = fb.font["OS/2"]
    os2.version = 4
    os2.fsSelection |= 0x80                    # use typo metrics
    os2.recalcUnicodeRanges(fb.font)           # tell apps which scripts are covered
    os2.ulCodePageRange1 = 0x20000007          # Latin 1 (1252), Latin 2 (1250), Cyrillic (1251), US-ASCII
    os2.ulCodePageRange2 = 0
    os2.usFirstCharIndex, os2.usLastCharIndex = 0x20, 0xFFFD if 0xFFFD in cmap else max(c for c in cmap if c <= 0xFFFF)
    fb.setupPost(isFixedPitch=1, underlinePosition=-120, underlineThickness=70, italicAngle=0.0)
    from fontTools.ttLib import newTable
    gasp = newTable("gasp"); gasp.version = 1; gasp.gaspRange = {8: 0x000A, 65535: 0x000F}
    fb.font["gasp"] = gasp
    fb.font["head"].fontRevision = float(VERSION)
    fb.font["head"].macStyle = 0
    out = ROOT / "fonts"
    out.mkdir(exist_ok=True)
    fb.save(out / "Swiz13-Regular.ttf")
    from fontTools.ttLib import TTFont
    f = TTFont(out / "Swiz13-Regular.ttf")
    f.flavor = "woff2"
    f.save(out / "Swiz13-Regular.woff2")
    (ROOT / "sources").mkdir(exist_ok=True)
    json.dump(provenance, open(ROOT / "sources" / "glyph-blend.json", "w"), indent=1)
    print("Built Swiz13:", len(cmap), "characters")


if __name__ == "__main__":
    main()
