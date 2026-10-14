"""Load the three donor fonts into one shared cell (1000 upm, 600 pitch, x-height ~550, cap ~730)."""
from math import hypot, radians, tan
from pathlib import Path

import numpy as np
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw
from scipy import ndimage
from shapely.geometry import Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sources"
# name -> (file, x scale, y scale)
# name -> (file, x scale, y scale, synthetic slant in degrees).  Martian Mono has no italic, so it is
# slanted here (about the middle of the x-height) to match the true italics of Maple Mono and Hack.
SLANT = 10.0
DONORS = {
    "martian": ("MartianMono-SemiCondensed-Light.ttf", 600 / 650, 600 / 650, SLANT),
    "maple": ("MapleMono-Italic.ttf", 1.0, 1.0, 0.0),
    "hack": ("Hack-Italic.ttf", 600 / 1233, 1000 / 2048, 0.0),
}


class _Flat(BasePen):
    def __init__(self, gs):
        super().__init__(gs)
        self.rings = []

    def _moveTo(self, p): self.rings.append([p])
    def _lineTo(self, p): self.rings[-1].append(p)

    def _curveToOne(self, a, b, c):
        p = self.rings[-1][-1]
        n = max(6, int((hypot(a[0]-p[0], a[1]-p[1]) + hypot(b[0]-a[0], b[1]-a[1]) + hypot(c[0]-b[0], c[1]-b[1])) / 40))
        for i in range(1, n + 1):
            t = i / n; u = 1 - t
            self.rings[-1].append((u**3*p[0]+3*u*u*t*a[0]+3*u*t*t*b[0]+t**3*c[0],
                                   u**3*p[1]+3*u*u*t*a[1]+3*u*t*t*b[1]+t**3*c[1]))

    def _qCurveToOne(self, a, b):
        p = self.rings[-1][-1]
        n = max(5, int((hypot(a[0]-p[0], a[1]-p[1]) + hypot(b[0]-a[0], b[1]-a[1])) / 40))
        for i in range(1, n + 1):
            t = i / n; u = 1 - t
            self.rings[-1].append((u*u*p[0]+2*u*t*a[0]+t*t*b[0], u*u*p[1]+2*u*t*a[1]+t*t*b[1]))

    def _closePath(self): pass
    def _endPath(self): pass


class Donor:
    def __init__(self, key):
        fn, self.sx, self.sy, self.slant = DONORS[key]
        self.tan = tan(radians(self.slant))
        self.font = TTFont(SRC / fn)
        self.cmap = self.font.getBestCmap()
        self.gs = self.font.getGlyphSet()

    def has(self, cp):
        return cp in self.cmap

    def advance(self, cp):
        return self.font["hmtx"][self.cmap[cp]][0] * self.sx

    def geometry(self, cp):
        pen = _Flat(self.gs)
        self.gs[self.cmap[cp]].draw(pen)
        rings = []
        for r in pen.rings:
            pts = [(x * self.sx + (y * self.sy - 275) * self.tan, y * self.sy) for x, y in r]
            if len(pts) >= 3:
                rings.append(pts)
        if not rings:
            return Polygon()
        area = lambda r: sum(x0*y1-x1*y0 for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]))
        areas = [area(r) for r in rings]
        lead = max(areas, key=abs)
        fills, holes = [], []
        for r, a in zip(rings, areas):
            poly = Polygon(r)
            poly = poly if poly.is_valid else poly.buffer(0)
            (fills if (a > 0) == (lead > 0) else holes).append(poly)
        g = unary_union(fills)
        return g.difference(unary_union(holes)) if holes else g


SS = 2   # pixels per font unit


def raster(geom, box):
    """Binary mask at SS pixels/unit over box=(x0,y0,x1,y1) (integers)."""
    x0, y0, x1, y1 = box
    w, h = (x1 - x0) * SS, (y1 - y0) * SS
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    polys = [geom] if geom.geom_type == "Polygon" else list(getattr(geom, "geoms", []))
    for p in polys:
        if p.geom_type != "Polygon" or p.is_empty:
            continue
        d.polygon([((x - x0) * SS, (y1 - y) * SS) for x, y in p.exterior.coords], fill=255)
        for i in p.interiors:
            d.polygon([((x - x0) * SS, (y1 - y) * SS) for x, y in i.coords], fill=0)
    return np.asarray(img) > 127


def sdf(mask):
    """Signed distance in font units, positive inside."""
    if not mask.any():
        return np.full(mask.shape, -999.0)
    inside = ndimage.distance_transform_edt(mask)
    outside = ndimage.distance_transform_edt(~mask)
    return np.where(mask, inside - 0.5, -(outside - 0.5)) / SS
