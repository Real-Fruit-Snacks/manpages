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
rm -rf "$DEST"; mkdir -p "$DEST"
export DEST

one() {
  dpkg-deb --fsys-tarfile "$1" 2>/dev/null \
    | tar -x -C "$DEST" --wildcards './usr/share/man/man[1-9]*' 2>/dev/null || true
}
export -f one

ls "$CACHE"/debs/*.deb | xargs -P "$(nproc)" -n 1 bash -c 'one "$1"' _
echo "==> extracted files: $(find "$DEST/usr/share/man" \( -type f -o -type l \) 2>/dev/null | wc -l)"
