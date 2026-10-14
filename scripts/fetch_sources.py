"""Optional: re-download the donor fonts that are available from npm.

Hack Italic, Google Sans Code Italic and Maple Mono Italic (Latin subset) come from npm packages;
Martian Mono is not fetched (the exact static file is in sources/).  Needs Node/npm.
Usage:  python3 scripts/fetch_sources.py
"""
import shutil, subprocess, tempfile
from pathlib import Path
from fontTools.ttLib import TTFont

SRC = Path(__file__).resolve().parents[1] / "sources"


def npm_pack(pkg, tmp):
    subprocess.run(["npm", "pack", pkg], cwd=tmp, check=True, capture_output=True)
    tgz = next(Path(tmp).glob("*.tgz"))
    subprocess.run(["tar", "xzf", tgz.name], cwd=tmp, check=True)
    return Path(tmp) / "package"


def woff2_to_ttf(src, dst):
    font = TTFont(src)
    font.flavor = None
    font.save(dst)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = npm_pack("hack-font@3.3.0", tmp)
        shutil.copy(pkg / "build/ttf/Hack-Italic.ttf", SRC / "Hack-Italic.ttf")
        shutil.copy(pkg / "LICENSE.md", SRC.parent / "licenses/HACK-LICENSE.md")
    with tempfile.TemporaryDirectory() as tmp:
        pkg = npm_pack("@fontsource/google-sans-code@5.3.2", tmp)
        woff2_to_ttf(pkg / "files/google-sans-code-latin-400-italic.woff2", SRC / "GoogleSansCode-Italic.ttf")
        woff2_to_ttf(pkg / "files/google-sans-code-math-400-normal.woff2", SRC / "GoogleSansCode-Math-Regular.ttf")   # arrows
    with tempfile.TemporaryDirectory() as tmp:
        pkg = npm_pack("@fontsource/maple-mono@5.3.0", tmp)
        woff2_to_ttf(pkg / "files/maple-mono-latin-400-italic.woff2", SRC / "MapleMono-Italic.ttf")
        woff2_to_ttf(pkg / "files/maple-mono-latin-400-normal.woff2", SRC / "MapleMono-Regular.ttf")   # for the comparison sheets
    print("Fetched Hack-Italic, GoogleSansCode-Italic MapleMono-Italic and MapleMono-Regular into sources/")


if __name__ == "__main__":
    main()
