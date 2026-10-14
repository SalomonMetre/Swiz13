"""Specimen sheets comparing Swiz13 with the upright versions of the fonts it draws on (same 600-unit pitch)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
ROOT = Path(__file__).resolve().parents[1]
PAPER, INK, MUTED, ACC, SMK = "#f3efe5", "#242720", "#737568", "#af4d30", "#1d4f8f"
FONTS = [("Swiz13", "fonts/Swiz13-Regular.ttf"),
         ("Martian Mono (SemiCondensed Light)", "sources/MartianMono-SemiCondensed-Light.ttf"),
         ("Maple Mono Regular", "sources/MapleMono-Regular.ttf"),
         ("Hack Regular (source of the 0)", "sources/Hack-Regular.ttf"),
         ("Google Sans Code Regular (source of Q, g, brackets)", "sources/GoogleSansCode-Regular.ttf")]
LABEL = ImageFont.truetype(str(ROOT / "sources/Hack-Regular.ttf"), 24)


def fit(path, pitch_px):
    """Font object whose advance width is pitch_px."""
    f = ImageFont.truetype(str(ROOT / path), 200)
    return ImageFont.truetype(str(ROOT / path), max(8, round(200 * pitch_px / f.getlength("a"))))


_CMAPS = {}


def covered(path, text):
    """Blank out characters a donor file does not contain (some donor files are Latin-only subsets)."""
    if path not in _CMAPS:
        _CMAPS[path] = set(TTFont(ROOT / path).getBestCmap())
    return "".join(ch if (ch == " " or ord(ch) in _CMAPS[path]) else " " for ch in text)


def sheet(name, lines, pitch, row_h, title, width=1700, heading=None, pad=70):
    height = 150 + len(FONTS) * (row_h * len(lines) + pad) + 40 + 40
    img = Image.new("RGB", (width, height), PAPER)
    d = ImageDraw.Draw(img)
    d.text((70, 48), title, font=LABEL, fill=ACC)
    y = 120
    for fam, path in FONTS:
        d.text((70, y), fam.upper(), font=LABEL, fill=SMK if fam.startswith("Swiz13") else MUTED)
        f = fit(path, pitch)
        for i, ln in enumerate(lines):
            d.text((70, y + 50 + i * row_h), covered(path, ln), font=f, fill=SMK if fam.startswith("Swiz13") else INK)
        y += row_h * len(lines) + pad
        d.line((70, y - 8, width - 70, y - 8), fill="#cbcbbd", width=2)
    img.save(ROOT / "specimens" / name)


sheet("Swiz13-Compare-1-Alphabet.png", ["abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "0123456789  il1 O0"],
      pitch=58, row_h=92, title="COMPARISON 1 / ALPHABET, CAPITALS, DIGITS  (same 600-unit pitch)")
sheet("Swiz13-Compare-2-Symbols-Accents.png", ["!?@#$%&*()[]{}<>=+-_/\\|;:'\",.~^`", "Élégant, naïf, déjà vu ç ñ ö ø å š ž ą ő", "Привет, мир! Жук ёж Щука"],
      pitch=50, row_h=84, title="COMPARISON 2 / SYMBOLS, ACCENTS, CYRILLIC")
sheet("Swiz13-Compare-3-Code.png", ["def f(x):  return x != 0 -> {1, 2}[i]", "if (a[0] >= b) { print(\"ok\"); }  // 0O il1|"],
      pitch=42, row_h=70, title="COMPARISON 3 / CODE")
sheet("Swiz13-Compare-4-Paragraph.png", ["The room was quiet, except for the keys.", "A short note became a page; a page became", "a letter. Each mark had somewhere to be."],
      pitch=44, row_h=72, title="COMPARISON 4 / TEXT")
# close-up of the letters that differ most between the donors
sheet("Swiz13-Compare-5-Closeup.png", ["agfjrty0&@", "{}[]()Qg%"], pitch=120, row_h=235,
      title="COMPARISON 5 / CLOSE-UP OF THE GLYPHS THAT DIFFER MOST", width=1500)
# the three hand-picked glyphs, large
sheet("Swiz13-Compare-6-Picked-Glyphs.png", ["a \u00e0 \u00e1 Q 0", "aQ0 Quad", "f g o ( )"], pitch=130, row_h=215,
      title="COMPARISON 6 / HAND-PICKED: upright a / Q, open g, brackets GSC / 0 Hack / f no tail / script o", width=1500, pad=130)
sheet("Swiz13-Compare-7-Sentences.png", ["Sphinx of black quartz, judge my vow.", "Pack my box with five dozen liquor jugs.",
      "0123456789 O0o il1| {}[]() <>=+-*/ @#&%$"], pitch=36, row_h=62,
      title="COMPARISON 7 / PANGRAMS AND CODE CHARACTERS", width=1700)

# one PDF with every sheet
from pathlib import Path as _P
sheets = sorted((ROOT / "specimens").glob("Swiz13-Compare-*.png"))
imgs = [Image.open(p).convert("RGB") for p in sheets]
imgs[0].save(ROOT / "specimens" / "Swiz13-Comparison-All.pdf", save_all=True, append_images=imgs[1:], resolution=130)
print("rendered", len(sheets), "comparison sheets")
