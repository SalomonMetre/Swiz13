"""Blend the three donors glyph by glyph through signed distance fields.

Each donor is stroke-matched to one target stem, then the fields are averaged
with role weights.  A donor whose shape disagrees with the others (a different
'a', 'g' or zero) is dropped for that glyph so nothing ghosts.
"""
import pickle, sys, unicodedata
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Polygon
from shapely import wkb
from skimage import measure

sys.path.insert(0, str(Path(__file__).parent))
from donors import DONORS, Donor, raster, sdf, ROOT, SS
from scipy import ndimage as ndi

STEM = {"martian": 92.3, "maple": 90.0, "hack": 98.1}
TARGET = 86.0
OUT = ROOT / "build"
_D = None
EXTRA_CHARS = "\u04d2\u04d3"   # Cyrillic a/A with diaeresis: not in Martian, built from the other donors
EXCLUDE = {"a": ("martian",), "0": ("hack",), "A": ("hack",), "|": ("hack",)}   # keep the single-storey cursive a


def weights_for(ch):
    if ch.isalpha() and ch.islower():
        return {"maple": .50, "hack": .27, "martian": .23}   # Maple Mono Italic has the cursive forms
    if ch.isalpha():
        return {"maple": .36, "martian": .34, "hack": .30}
    if ch.isdigit():
        return {"hack": .36, "maple": .34, "martian": .30}
    return {"hack": .36, "maple": .34, "martian": .30}


def _donors():
    global _D
    if _D is None:
        _D = {k: Donor(k) for k in DONORS}
    return _D


def iou(a, b):
    u = (a | b).sum()
    return (a & b).sum() / u if u else 1.0


def _base(ch):
    b = unicodedata.normalize("NFD", ch)[0]
    return {"\u0430": "a", "\u0410": "A"}.get(b, b)


def _clean(shape, speck=300):
    polys = [shape] if shape.geom_type == "Polygon" else list(shape.geoms)
    out = []
    for p in polys:
        if p.area < speck:
            continue
        holes = [h for h in p.interiors if Polygon(h).area >= speck]
        out.append(Polygon(p.exterior, holes))
    from shapely.ops import unary_union
    return unary_union(out) if out else shape


def blend_glyph(cp):
    D = _donors()
    ch = chr(cp)
    geoms = {k: d.geometry(cp) for k, d in D.items() if d.has(cp)}
    geoms = {k: g for k, g in geoms.items() if not g.is_empty}
    adv = {k: D[k].advance(cp) for k in D if D[k].has(cp)}
    if not geoms:
        return cp, None, 0, {}
    xs0 = min(g.bounds[0] for g in geoms.values()); ys0 = min(g.bounds[1] for g in geoms.values())
    xs1 = max(g.bounds[2] for g in geoms.values()); ys1 = max(g.bounds[3] for g in geoms.values())
    box = (int(xs0) - 40, int(ys0) - 40, int(xs1) + 41, int(ys1) + 41)
    masks = {k: raster(g, box) for k, g in geoms.items()}
    w = {k: v for k, v in weights_for(ch).items() if k in geoms and k not in EXCLUDE.get(_base(ch), ())}
    if not w:
        w = {k: v for k, v in weights_for(ch).items() if k in geoms}
    ref = max(w, key=w.get)
    fields = {k: sdf(masks[k]) + (TARGET - STEM[k]) / 2 for k in masks}
    H, Wd = fields[ref].shape
    gy, gx = np.mgrid[0:H, 0:Wd].astype(np.float32)

    def img8(f):
        return np.clip(f * 4 + 128, 0, 255).astype(np.uint8)

    flows, warped = {}, {}
    for k in masks:
        if k == ref:
            flows[k] = np.zeros((H, Wd, 2), np.float32)
        else:
            flows[k] = cv2.calcOpticalFlowFarneback(img8(fields[ref]), img8(fields[k]), None,
                                                    0.5, 5, 31, 6, 7, 1.5, 0)
        warped[k] = cv2.remap(fields[k].astype(np.float32), gx + flows[k][..., 0], gy + flows[k][..., 1],
                              cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    # drop a donor that still disagrees with the reference after registration
    used = dict(w)
    for k in list(masks):
        if k != ref and iou(warped[k] > 0, fields[ref] > 0) < 0.60:
            used.pop(k, None)
    tot = sum(used.values())
    used = {k: v / tot for k, v in used.items()}
    # mean displacement: the blended glyph sits at the weighted average position
    m = sum(wt * flows[k] for k, wt in used.items())
    xm = gx - m[..., 0]; ym = gy - m[..., 1]
    field = 0
    for k, wt in used.items():
        fx = cv2.remap(flows[k][..., 0], xm, ym, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        fy = cv2.remap(flows[k][..., 1], xm, ym, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        field = field + wt * cv2.remap(fields[k].astype(np.float32), xm + fx, ym + fy,
                                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    field = ndi.gaussian_filter(field, 1.3 * SS)
    field = np.pad(field, 1, constant_values=-50)
    cs = measure.find_contours(field, 0.0)
    x0, y0, x1, y1 = box
    h = y1 - y0
    polys = []
    for c in cs:
        pts = [(x0 + (col - 1 + 0.5) / SS, y1 - (row - 1 + 0.5) / SS) for row, col in c]
        if len(pts) >= 4:
            p = Polygon(pts)
            p = p if p.is_valid else p.buffer(0)
            if not p.is_empty:
                polys.append(p)
    shape = None
    for p in sorted(polys, key=lambda q: -q.area):
        shape = p if shape is None else shape.symmetric_difference(p)
    if shape is None or shape.is_empty:
        return cp, None, np.mean(list(adv.values())) if adv else 600, used
    shape = _clean(shape).simplify(0.6, preserve_topology=True)
    return cp, wkb.dumps(shape), (adv.get("maple") or 600 if adv else 600), used


def main():
    OUT.mkdir(exist_ok=True)
    mart = Donor("martian")
    cps = sorted(set(mart.cmap) | {ord(c) for c in EXTRA_CHARS})
    only = sys.argv[1] if len(sys.argv) > 1 else None
    if only:
        cps = [ord(c) for c in only]
    with Pool() as pool:
        res = pool.map(blend_glyph, cps, chunksize=4)
    data = {cp: (g, adv, used) for cp, g, adv, used in res}
    name = "blend_test.pkl" if only else "blend.pkl"
    pickle.dump(data, open(OUT / name, "wb"))
    print("blended", len(data), "glyphs ->", name)
    for cp, v in sorted(data.items()):
        if len(v[2]) < 3 and only: print(chr(cp), 'uses', {k: round(x, 2) for k, x in v[2].items()})
    dropped = sum(1 for v in data.values() if len(v[2]) < 3)
    print("glyphs with a donor dropped:", dropped)


if __name__ == "__main__":
    main()
