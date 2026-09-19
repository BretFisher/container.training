#!/bin/sh
# Build every deck: index.html, past.html, and one foo.yml.html per foo.yml.
# Exits non-zero on the first failing deck so watchers and CI see the error.
#
# Usage:  ./build.sh [once]
# Env:    SLIDES_ZIP=1   also create slides.zip (Netlify sets this; not needed in dev)
set -eu

case "${1:-once}" in
  once) ;;
  forever)
    echo >&2 "'forever' was removed. Use 'make serve' (Compose watch) instead."
    exit 2
    ;;
  *)
    echo >&2 "usage: $0 [once]"
    exit 2
    ;;
esac

# Remove leftovers from a previous failed build.
rm -f ./*.yml.html.tmp

./index.py

for YAML in *.yml; do
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
