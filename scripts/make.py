"""Run the whole Swiz13 pipeline:  python3 scripts/make.py [--skip-blend] [--no-specimens]

  1. blend.py      blend Martian Mono, Maple Mono and Hack glyph by glyph   (slow: ~10-15 min)
  2. overrides.py  take ( ) [ ] { }, Q and g (open bottom loop) from Google Sans Code; cut the tail of f, draw the script o
  3. build.py      typewriter finish + assemble fonts/Swiz13-Regular.ttf and .woff2
  4. specimen.py / compare.py   render the specimen sheets (optional)
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent


def run(script, *args):
    print(f"\n==> {script} {' '.join(args)}", flush=True)
    subprocess.run([sys.executable, "-I", str(HERE / script), *args], check=True, cwd=ROOT)


def main():
    flags = set(sys.argv[1:])
    if "--skip-blend" not in flags or not (ROOT / "build" / "blend.pkl").exists():
        (ROOT / "build" / "blend-raw.pkl").unlink(missing_ok=True)
        run("blend.py")
    run("overrides.py")
    run("build.py")
    if "--no-specimens" not in flags:
        run("specimen.py")
        run("compare.py")
    print("\nDone. Fonts are in fonts/")


if __name__ == "__main__":
    main()
