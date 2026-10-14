"""Hand-picked glyph overrides applied on top of the blend (scaled to the 600-unit cell and thinned to
the blend's stroke weight); the typewriter finish is applied later by build.py."""
import pickle
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from shapely import wkb
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
from donors import ROOT, _Flat

SRC = ROOT / "sources"
# (characters, source font, x scale, y scale, thinning in units, tag, keep islands inside counters)
#  - ( ) { } [ ] come from Google Sans Code Italic (they are de-slanted with everything else)
#  - Q from Google Sans Code Regular and 0 from Hack Regular stay upright: the "-upright" tag makes
#    build.py skip the de-slanting for them.
OVERRIDES = [
    ("(){}[]", "GoogleSansCode-Italic.ttf", .5, .5, 3.5, "google-sans-code", False),
    ("Q", "GoogleSansCode-Regular.ttf", .5, .5, 3.5, "google-sans-code-upright", False),
    ("+<=>|¬±×÷⁄↑↓−", "GoogleSansCode-Regular.ttf", .5, .5, 3.5, "google-sans-code-upright", False),   # maths symbols
    ("~", "GoogleSansCode-Regular.ttf", .5, .5, 0, "google-sans-code-clean-upright", False),   # the tilde: exact outline, no typewriter finish
    ("←→", "GoogleSansCode-Math-Regular.ttf", .5, .5, 3.5, "google-sans-code-upright", False),
    ("!#$%&*,-./:;?\\^_`¡¢£¤¥¦§¨«¯°´¶·¸»¿˚˜–—‘’‚“”„•…‹›€™", "GoogleSansCode-Regular.ttf", .5, .5, 3.5, "google-sans-code-upright", False),   # special characters
    ("©®", "GoogleSansCode-Regular.ttf", .5, .5, 3.5, "google-sans-code-upright", True),   # letters inside the circles
    ("0", "Hack-Regular.ttf", 600 / 1233, 1000 / 2048, 6.4, "hack-upright", True),   # Hack's 0 has an inner slash
]


# Straight typewriter quotes, drawn rather than borrowed: perfectly vertical bars (no lean), long and
# heavy enough to stay visible.  Tag "straight-upright": not de-slanted, no per-letter tilt in build.py.
QUOTE_TOP, QUOTE_BOTTOM, QUOTE_RADIUS = 695, 500, 43


def _bars(xs):
    return unary_union([LineString([(x, QUOTE_TOP), (x, QUOTE_BOTTOM)]).buffer(QUOTE_RADIUS, 24) for x in xs])


DRAWN = {'"': _bars([212, 388]), "'": _bars([300])}


# o (lowercase only): Martian Mono's o exactly.  Tag "-upright": not de-slanted.
def drawn_o():
    """Martian Mono's o, exactly: a plain round o (it used to carry a hairline; that is gone)."""
    mf = TTFont(SRC / "MartianMono-SemiCondensed-Light.ttf")
    return glyph(mf, mf.getBestCmap(), mf.getGlyphSet(), ord("o"), 600 / 650, 600 / 650)


def glyph(font, cmap, glyphset, cp, sx, sy, islands=False):
    pen = _Flat(glyphset)
    glyphset[cmap[cp]].draw(pen)
    rings = [Polygon([(x * sx, y * sy) for x, y in r]) for r in pen.rings if len(r) >= 3]
    rings = [r if r.is_valid else r.buffer(0) for r in rings]
    area = lambda r: sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1)
                         in zip(r.exterior.coords, list(r.exterior.coords)[1:]))
    lead = max(rings, key=lambda r: r.area)
    lead_dir = area(lead) > 0
    if islands:
        shape = Polygon()
        for r in sorted(rings, key=lambda r: -r.area):   # biggest first, so islands inside a counter come back
            shape = shape.union(r) if (area(r) > 0) == lead_dir else shape.difference(r)
        return shape
    fills = [r for r in rings if (area(r) > 0) == lead_dir]
    holes = [r for r in rings if r not in fills]
    shape = unary_union(fills)
    return shape.difference(unary_union(holes)) if holes else shape


# --- f and g -------------------------------------------------------------------------------------
# f: the blend's upper part is kept, its small tail (the hook under the baseline) is cut off.  The cut is made
#    in the blend's own (slanted) space, so build.py de-slants the result like every other letter.
F_CUT = 0
# g: Google Sans Code Regular's g (upright, tag "-upright" so build.py does not de-slant it) with the lower loop
#    opened: the loop's whole left-hand wall is removed, so the link comes down, turns into the horizontal
#    stroke, which sweeps round to the right and ends in a free hook at the bottom left.
G_SCALE = .525                 # scaled so the bowl meets the x-height (~550)
G_CUT = unary_union([box(0, -190, 260, -50),
                     Polygon([(0, -60), (0, 70), (156, 46), (215, -8), (260, -60)])])   # region removed


def tailless_f(raw_shape):
    return raw_shape.intersection(box(-200, F_CUT, 800, 1000))


def open_g():
    font = TTFont(SRC / "GoogleSansCode-Regular.ttf")
    cmap, gs = font.getBestCmap(), font.getGlyphSet()
    g = glyph(font, cmap, gs, ord("g"), G_SCALE, G_SCALE).buffer(-3.5, 16)
    g = g.difference(G_CUT).buffer(-5, 16).buffer(5, 16)      # the buffers round the cut ends
    return g.simplify(.6, preserve_topology=True)


R_BOTTOM, R_HEIGHT, R_WIDTH, R_CENTER = -9, 571, 430, 290
R_TOP_WIDEN = .14     # the r's top is this much wider (the bar and the tops of the legs), the foot unchanged
R_STROKE = 86         # the one stroke weight of the r (measured to match the u: about 85 units)
# the centre lines of the ligatured r's two legs, read off sources/r-reference.png (x, y in picture pixels, y down): the
# short left leg that curls out to the left and the long right leg that ends in a foot; the top bar joins them
R_LEGS = [[(130, 33), (130, 140), (112, 195), (72, 225), (40, 243)],
          [(390, 33), (355, 150), (318, 260), (305, 350), (318, 420), (360, 455), (445, 458)]]


def drawn_r():
    import numpy as np
    from scipy.interpolate import splprep, splev
    from shapely.geometry import LineString, box
    from shapely.ops import transform, unary_union
    lines = []
    for pts in R_LEGS:
        pts = np.array(pts, float)
        t = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
        tck, _ = splprep([pts[:, 0], pts[:, 1]], u=t / t[-1], s=len(pts) * 3.0, k=3)
        lines.append(np.array(splev(np.linspace(0, 1, 80), tck)).T)
    allp = np.vstack(lines)
    # scale the centre lines, not the outline, so the stroke keeps one weight everywhere; the finished outline (lines plus
    # half a stroke each side) fills the target box, with the legs' flat tops forming the top edge
    w = R_STROKE
    sx = (R_WIDTH - w) / (allp[:, 0].max() - allp[:, 0].min())
    sy = (R_HEIGHT - w / 2) / (allp[:, 1].max() - allp[:, 1].min())
    cx = (allp[:, 0].max() + allp[:, 0].min()) / 2
    ytop = allp[:, 1].min()
    top = R_BOTTOM + R_HEIGHT
    legs = []
    for pts in lines:
        X = R_CENTER + (pts[:, 0] - cx) * sx
        Y = top - (pts[:, 1] - ytop) * sy
        legs.append(LineString(list(zip(X, Y))))
    parts = [l.buffer(w / 2, 16, cap_style=2, join_style=2) for l in legs]
    # the top bar joins the two legs and runs flush with their outer edges
    xl, xr = legs[0].coords[0][0] - w / 2, legs[1].coords[0][0] + w / 2
    shape = unary_union(parts + [box(xl, top - w, xr, top)]).intersection(box(-1000, -1000, 2000, top))   # a flat top edge
    mid = R_BOTTOM + R_HEIGHT * .45
    shape = transform(lambda xs, ys, zs=None: (R_CENTER + (np.asarray(xs) - R_CENTER) * (1 + R_TOP_WIDEN * np.clip(
        (np.asarray(ys) - mid) / (top - mid), 0, 1)), ys), shape.segmentize(4))
    return shape.buffer(-3, 16).buffer(3, 16).simplify(.5, preserve_topology=True)


S_BOTTOM, S_HEIGHT, S_WIDTH, S_CENTER = -7, 565, 430, 300
S_STROKE = 84         # the s's one stroke weight
# centre lines of the lowercase s, read off the user's picture (x, y in picture pixels, y down): the short upper-left
# arm that curls out to the left, and the long stroke that drops from the top, wraps round the bottom and ends at the left
S_STROKES = [[(165, 100), (160, 160), (130, 215), (90, 250), (58, 268)],
             [(229, 100), (235, 170), (285, 250), (310, 320), (300, 390), (250, 440), (180, 452), (115, 432), (70, 392)]]


def drawn_s():
    import numpy as np
    from scipy.interpolate import splprep, splev
    from shapely.geometry import LineString, box
    from shapely.ops import unary_union
    lines = []
    for pts in S_STROKES:
        pts = np.array(pts, float)
        t = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
        tck, _ = splprep([pts[:, 0], pts[:, 1]], u=t / t[-1], s=len(pts) * 3.0, k=3)
        lines.append(np.array(splev(np.linspace(0, 1, 90), tck)).T)
    allp = np.vstack(lines)
    w = S_STROKE
    sx = (S_WIDTH - w) / (allp[:, 0].max() - allp[:, 0].min())
    sy = (S_HEIGHT - w / 2) / (allp[:, 1].max() - allp[:, 1].min())
    cx = (allp[:, 0].max() + allp[:, 0].min()) / 2
    ytop = allp[:, 1].min()
    top = S_BOTTOM + S_HEIGHT
    legs = [LineString([(S_CENTER + (x - cx) * sx, top - (y - ytop) * sy) for x, y in pts]) for pts in lines]
    parts = [l.buffer(w / 2, 16, cap_style=2, join_style=2) for l in legs]
    xl, xr = legs[0].coords[0][0] - w / 2, legs[1].coords[0][0] + w / 2
    shape = unary_union(parts + [box(xl, top - w * .9, xr, top)]).intersection(box(-1000, -1000, 2000, top))
    return shape.buffer(-3, 16).buffer(3, 16).simplify(.5, preserve_topology=True)


L_STRAIGHTEN = 8     # extra de-slant of the l, in degrees (its design is untouched)


def straight_l(raw):
    from math import radians, tan
    from shapely import affinity
    return affinity.affine_transform(raw, [1, -tan(radians(L_STRAIGHTEN)), 0, 1, tan(radians(L_STRAIGHTEN)) * 275, 0])


def main():
    path = ROOT / "build" / "blend.pkl"
    raw_path = ROOT / "build" / "blend-raw.pkl"      # the blend before any override, so a rerun is idempotent
    if not raw_path.exists():
        raw_path.write_bytes(path.read_bytes())
    data = pickle.load(open(raw_path, "rb"))
    for chars, fname, sx, sy, thin, tag, islands in OVERRIDES:
        font = TTFont(SRC / fname)
        cmap, gs = font.getBestCmap(), font.getGlyphSet()
        for ch in chars:
            shape = glyph(font, cmap, gs, ord(ch), sx, sy, islands).buffer(-thin, 16).simplify(.6, preserve_topology=True)
            old = data[ord(ch)]
            data[ord(ch)] = (wkb.dumps(shape), old[1], {tag: 1.0})
    for ch, shape in DRAWN.items():
        old = data[ord(ch)]
        data[ord(ch)] = (wkb.dumps(shape), old[1], {"drawn-straight-upright": 1.0})
    old = data[ord("o")]
    data[ord("o")] = (wkb.dumps(drawn_o()), old[1], {"drawn-script-upright": 1.0})
    old = data[ord("f")]
    data[ord("f")] = (wkb.dumps(tailless_f(wkb.loads(old[0]))), old[1], old[2])
    old = data[ord("s")]
    data[ord("s")] = (wkb.dumps(drawn_s()), old[1], {"drawn-script-upright": 1.0})
    old = data[ord("r")]
    data[ord("r")] = (wkb.dumps(drawn_r()), old[1], {"drawn-script-upright": 1.0})
    old = data[ord("l")]
    data[ord("l")] = (wkb.dumps(straight_l(wkb.loads(old[0]))), old[1], old[2])
    old = data[ord("g")]
    data[ord("g")] = (wkb.dumps(open_g()), old[1], {"google-sans-code-upright": 1.0})
    pickle.dump(data, open(path, "wb"))
    print("overrides applied:", " ".join(o[0] for o in OVERRIDES), "".join(DRAWN), "f(tailless) g(open) l(straight) r(ligatured) s(script) o(Martian, lowercase only)")


if __name__ == "__main__":
    main()
