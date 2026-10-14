# Donor fonts

| File | Family | License | Used for |
|---|---|---|---|
| `MapleMono-Italic.ttf` | Maple Mono Italic (npm `@fontsource/maple-mono` 5.3.0, Latin subset) | SIL OFL 1.1 | blend; the main source of cursive forms for lowercase (Basic Latin, Latin-1 and part of Latin Extended; no Cyrillic in this subset) |
| `MapleMono-Regular.ttf` | Maple Mono Regular, upright (npm `@fontsource/maple-mono` 5.3.0, Latin subset) | SIL OFL 1.1 | comparison sheets only |
| `Hack-Italic.ttf` | Hack 3.3.0 Italic (npm `hack-font`) | MIT + Bitstream Vera | blend; also supplies Cyrillic and the rare Latin letters Maple's subset lacks |
| `MartianMono-SemiCondensed-Light.ttf` | Martian Mono (SemiCondensed, Light) | SIL OFL 1.1 | blend, slanted 10 degrees in code (`SLANT` in `donors.py`) because Martian Mono has no italic; defines the 511-character set |
| `GoogleSansCode-Italic.ttf` | Google Sans Code 400 Italic (npm `@fontsource/google-sans-code` 5.3.2) | SIL OFL 1.1 | the glyphs `( ) [ ] { }` |
| `o-reference.jpg` | the reference picture of the script `o` supplied for this project | the user's own reference | traced and straightened by `overrides.py` to make the lowercase `o` |
| `UprightReference-Regular.ttf` | upright drawing of the same style, made for this project | SIL OFL 1.1 | supplies the lowercase `a` and its accented forms (copied as is) |
| `GoogleSansCode-Regular.ttf` | Google Sans Code 400 (upright) | SIL OFL 1.1 | the capital `Q` and the lowercase `g` (with its bottom loop opened in `overrides.py`) |
| `Hack-Regular.ttf` | Hack 3.3.0 Regular (upright) | MIT + Bitstream Vera | the digit `0` |

For the full Maple Mono Italic (all scripts) download MapleMono-Italic.ttf from
https://github.com/subframe7536/maple-font/releases and drop it in `sources/` replacing the file above;
the build uses whatever it finds. Martian Mono: https://github.com/evilmartians/martian-mono

`glyph-blend.json` is written by the build and records the donor weights used for each character.
