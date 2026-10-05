#!/bin/sh
# Build all decks and catalogs, or only SLIDES_DECK when it is set.
# Exits non-zero on the first failing deck so watchers and CI see the error.
#
# Usage:  ./build.sh [once|check]
# Env:    SLIDES_DECK=<filename>.yml   compile only this deck; skip catalogs
# Env:    SLIDES_ZIP=1   also create slides.zip (Netlify sets this; not needed in dev)
set -eu

case "${1:-once}" in
  once|check) ;;
  forever)
    echo >&2 "'forever' was removed. Use 'make serve' (Compose watch) instead."
    exit 2
    ;;
  *)
    echo >&2 "usage: $0 [once|check]"
    exit 2
    ;;
esac

# Archives always include every deck. Treat the selector as a filename,
# never as shell syntax, and reject paths or option-like names.
selected=${SLIDES_DECK:-}
if [ "${SLIDES_ZIP:-}" = 1 ]; then selected=; fi
if [ -n "$selected" ]; then
  case "$selected" in
    *[!a-zA-Z0-9_.-]*|[.-]*) echo >&2 "Invalid SLIDES_DECK: use a .yml filename in slides/"; exit 2 ;;
    *.yml) ;;
    *) echo >&2 "Invalid SLIDES_DECK: use a .yml filename in slides/"; exit 2 ;;
  esac
  [ -f "$selected" ] || { echo >&2 "Deck not found: $selected"; exit 2; }
fi
[ "${1:-once}" != check ] || exit 0

if [ -n "$selected" ]; then
  echo "Building deck: $selected"
  set -- "$selected"
  rm -f "$selected.html.tmp"
else
  echo "Building all decks."
  set -- *.yml
  rm -f ./*.yml.html.tmp
  ./index.py
fi

for YAML do
  # Write to a temp file, then rename, so the web server never serves a
  # half-written deck and a failed build leaves the previous HTML in place.
  ./markmaker.py "$YAML" > "$YAML.html.tmp"
  mv "$YAML.html.tmp" "$YAML.html"
done

if [ "${SLIDES_ZIP:-}" = 1 ]; then
  rm -f slides.zip
  zip -qr slides.zip . -x 'fragments/*' '*.tmp'
  echo "Created slides.zip archive."
fi
