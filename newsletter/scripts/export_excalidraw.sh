#!/usr/bin/env bash
#
# Export .excalidraw files to SVG (and optionally PNG) for newsletter diagrams.
# Requires: Node.js, npx, excalidraw-brute-export-cli (installs Playwright + Firefox).
#
# Usage:
#   ./export_excalidraw.sh                    # Export all .excalidraw in excalidraw/
#   ./export_excalidraw.sh indexing-btree      # Export single file
#   ./export_excalidraw.sh --png               # Also export PNGs to plots/png/
#
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLOTS_DIR="$REPO/newsletter/plots"
EXCALIDRAW_DIR="$PLOTS_DIR/excalidraw"
SVG_DIR="$PLOTS_DIR/svg"
PNG_DIR="$PLOTS_DIR/png"

export_png=false
filter=""

for arg in "$@"; do
  case "$arg" in
    --png) export_png=true ;;
    *) filter="$arg" ;;
  esac
done

mkdir -p "$SVG_DIR"
$export_png && mkdir -p "$PNG_DIR"

if [ ! -d "$EXCALIDRAW_DIR" ]; then
  echo "Excalidraw dir not found: $EXCALIDRAW_DIR"
  exit 1
fi

# Ensure excalidraw-brute-export-cli is available
if ! npx excalidraw-brute-export-cli --help &>/dev/null; then
  echo "Installing excalidraw-brute-export-cli (may install Playwright + Firefox)..."
  npx --yes excalidraw-brute-export-cli --help &>/dev/null || true
fi

# Count total for progress bar
total=0
for f in "$EXCALIDRAW_DIR"/*.excalidraw; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .excalidraw)
  if [ -n "$filter" ] && [ "$name" != "$filter" ]; then continue; fi
  total=$((total + 1))
done

count=0
for f in "$EXCALIDRAW_DIR"/*.excalidraw; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .excalidraw)
  if [ -n "$filter" ] && [ "$name" != "$filter" ]; then
    continue
  fi
  count=$((count + 1))
  pct=0
  [ "$total" -gt 0 ] && pct=$((count * 100 / total))
  printf "[%d/%d] (%d%%) Exporting: %s\n" "$count" "$total" "$pct" "$name"
  npx --yes excalidraw-brute-export-cli \
    -i "$f" \
    -o "$SVG_DIR/$name.svg" \
    -f svg \
    -s 2 \
    -b true
  if $export_png; then
    npx --yes excalidraw-brute-export-cli \
      -i "$f" \
      -o "$PNG_DIR/$name.png" \
      -f png \
      -s 2 \
      -b true
  fi
done

echo ""
echo "Exported $count diagram(s) to $SVG_DIR"
if $export_png; then echo "PNGs written to $PNG_DIR"; fi
