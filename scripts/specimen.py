from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "fonts/Swiz13-Regular.ttf")
PAPER, INK, MUTED, ACC = "#f3efe5", "#242720", "#737568", "#af4d30"
img = Image.new("RGB", (1600, 1500), PAPER)
d = ImageDraw.Draw(img)
def t(x, y, s, size=28, c=INK): d.text((x, y), s, fill=c, font=ImageFont.truetype(FONT, size))
t(90, 60, "SWIZ13 / TYPE SPECIMEN", 24, ACC); t(1290, 60, "VERSION 1.0", 24, ACC)
t(82, 120, "Swiz13", 170); t(92, 330, "Martian, Maple and Hack, cursive forms, standing upright.", 38)
t(92, 392, "REGULAR  /  600 UNIT PITCH  /  513 CHARACTERS", 22, MUTED)
t(90, 470, "THE LETTERS", 22, ACC)
t(88, 520, "abcdefghijklmnopqrstuvwxyz", 74); t(88, 610, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", 74)
t(88, 700, "0123456789  il1 / O0  @&?!", 66)
t(90, 830, "ON PAPER", 22, ACC)
for i, l in enumerate(["The room was quiet, except for the keys.", "A short note became a page; a page became",
                       "a letter. Each mark had somewhere to be.", "Élégant, naïf, déjà vu. Привет, мир!"]):
    t(90, 880 + i * 58, l, 47)
t(90, 1150, "AT WORK", 22, ACC)
d.rounded_rectangle((90, 1200, 1510, 1440), radius=14, fill=INK)
for i, l in enumerate(['def write_letter(message):', '    for line in message.splitlines():', '        print(f"> {line}")  # != <= -> {}']):
    t(126, 1225 + i * 50, l, 36, PAPER)
img.save(ROOT / "specimens/Swiz13-Specimen.png")
