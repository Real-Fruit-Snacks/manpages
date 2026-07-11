#!/usr/bin/env bash
# run_all.sh — full pipeline: fetch -> unpack -> extract -> convert -> build -> copy.
# usage: run_all.sh <cache-dir> <workdir> <repo-docs-path>
# env:   PKG_LIMIT etc. pass through to fetch.sh
set -euo pipefail
CACHE=${1:?usage: run_all.sh <cache-dir> <workdir> <repo-docs>}
WORK=${2:?usage: run_all.sh <cache-dir> <workdir> <repo-docs>}
DOCS=${3:?usage: run_all.sh <cache-dir> <workdir> <repo-docs>}
HERE=$(dirname "$(readlink -f "$0")")

bash "$HERE/fetch.sh" "$CACHE"
bash "$HERE/unpack.sh" "$CACHE" "$WORK"
bash "$HERE/extract.sh" "$WORK/extracted/usr/share/man" "$WORK"
bash "$HERE/convert.sh" "$WORK"

OUT=$WORK/out
rm -rf "$OUT"; mkdir -p "$OUT"
python3 "$HERE/build_site.py" --work "$WORK" --out "$OUT"

echo "==> copying generated site into $DOCS"
rm -rf "$DOCS/man" "$DOCS/data" "$DOCS/browse"
cp -r "$OUT/man" "$OUT/data" "$DOCS/"
for extra in sw.js about.html browse; do
  [ -e "$OUT/$extra" ] && cp -r "$OUT/$extra" "$DOCS/"
done
echo "==> done: $(find "$DOCS/man" -name '*.html' | wc -l) pages in $DOCS/man"
