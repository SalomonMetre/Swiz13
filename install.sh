#!/usr/bin/env bash
# Install / uninstall Swiz13 on Linux.
#   ./install.sh                 install for the current user  (~/.local/share/fonts/Swiz13)
#   sudo ./install.sh --system   install for all users          (/usr/local/share/fonts/Swiz13)
#   ./install.sh --monospace     also make Swiz13 the preferred "monospace" font (fontconfig alias, per user)
#   ./install.sh --uninstall     remove it again (add --system for the system-wide copy)
set -euo pipefail
cd "$(dirname "$0")"

SYSTEM=0; UNINSTALL=0; MONO=0
for a in "$@"; do
  case "$a" in
    --system) SYSTEM=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --monospace) MONO=1 ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "unknown option: $a (see --help)" >&2; exit 2 ;;
  esac
done

if [ "$SYSTEM" = 1 ]; then
  DEST="/usr/local/share/fonts/Swiz13"
  CONF_DIR="/etc/fonts/conf.d"
else
  DEST="${XDG_DATA_HOME:-$HOME/.local/share}/fonts/Swiz13"
  CONF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/fontconfig/conf.d"
fi

refresh() {
  if command -v fc-cache >/dev/null; then
    fc-cache -f "$1" >/dev/null 2>&1 || true
    fc-cache -f >/dev/null 2>&1 || true
  else
    echo "note: fc-cache not found (install 'fontconfig'); log out and in, or restart apps, to pick the font up."
  fi
}

if [ "$UNINSTALL" = 1 ]; then
  rm -rf "$DEST" "$CONF_DIR/60-swiz13-monospace.conf"
  refresh "$(dirname "$DEST")"
  echo "Removed Swiz13 from $DEST"
  exit 0
fi

TTF="fonts/Swiz13-Regular.ttf"
if [ ! -f "$TTF" ]; then
  echo "error: $TTF not found. Run ./build.sh first." >&2; exit 1
fi

if [ "$SYSTEM" = 1 ] && [ "$(id -u)" -ne 0 ]; then
  echo "error: --system needs root. Run: sudo ./install.sh --system" >&2; exit 1
fi

mkdir -p "$DEST"
install -m 0644 "$TTF" "$DEST/"
install -m 0644 licenses/OFL.txt licenses/HACK-LICENSE.md "$DEST/"
if [ "$MONO" = 1 ]; then
  mkdir -p "$CONF_DIR"
  install -m 0644 contrib/60-swiz13-monospace.conf "$CONF_DIR/"
fi
refresh "$(dirname "$DEST")"

echo "Installed to $DEST"
if command -v fc-list >/dev/null; then
  LISTED="$(fc-list : family file 2>/dev/null | grep -i Swiz13 || true)"   # no 'grep -q' in a pipe: pipefail would misfire
  if [ -n "$LISTED" ]; then
    echo "Verified: $(echo "$LISTED" | head -1)"
  else
    echo "warning: fontconfig does not list Swiz13 yet. Try 'fc-cache -fv' and restart your applications."
  fi
fi
echo "Use it by choosing the font family \"Swiz13\" in your editor / terminal (see README.md)."
