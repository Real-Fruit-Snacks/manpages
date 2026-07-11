#!/usr/bin/env bash
# unpack.sh — extract usr/share/man from every cached .deb into one tree.
# Known limitation: if two packages ship the same page path, last write wins.
#
# usage: unpack.sh <cache-dir> <workdir>
set -euo pipefail
CACHE=${1:?usage: unpack.sh <cache-dir> <workdir>}
WORK=${2:?usage: unpack.sh <cache-dir> <workdir>}
CACHE=$(readlink -f "$CACHE"); mkdir -p "$WORK"; WORK=$(readlink -f "$WORK")
DEST=$WORK/extracted
MANIF=$WORK/manifests
rm -rf "$DEST" "$MANIF"; mkdir -p "$DEST" "$MANIF"
export DEST MANIF

one() {
  local deb=$1 base pkg ver
  base=${deb##*/}; base=${base%.deb}
  pkg=${base%%_*}
  ver=${base#*_}; ver=${ver%_*}; ver=${ver//%3a/:}
  dpkg-deb --fsys-tarfile "$deb" 2>/dev/null \
    | tar -xv -C "$DEST" --wildcards './usr/share/man/man[1-9]*' 2>/dev/null \
    | awk -v p="$pkg" -v v="$ver" -F/ '/[^/]$/ { print $(NF-1) "/" $NF "\t" p "\t" v }' \
    > "$MANIF/$base.tsv" || true
}
export -f one

ls "$CACHE"/debs/*.deb | xargs -d '\n' -P "$(nproc)" -n 1 bash -c 'one "$1"' _
cat "$MANIF"/*.tsv > "$WORK/filemap.tsv" 2>/dev/null || : > "$WORK/filemap.tsv"
echo "==> extracted files: $(find "$DEST/usr/share/man" \( -type f -o -type l \) 2>/dev/null | wc -l)"
echo "==> filemap: $(wc -l < "$WORK/filemap.tsv") entries"
