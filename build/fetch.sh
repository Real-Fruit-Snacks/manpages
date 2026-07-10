#!/usr/bin/env bash
# fetch.sh — download Ubuntu indexes and every main-component .deb that ships
# man pages, into a local cache. Idempotent: already-cached debs are skipped.
#
# usage: fetch.sh <cache-dir>
# env:   MIRROR, SUITES, PKG_LIMIT (0=all), JOBS
set -euo pipefail
CACHE=${1:?usage: fetch.sh <cache-dir>}
mkdir -p "$CACHE"; CACHE=$(readlink -f "$CACHE")
MIRROR=${MIRROR:-http://archive.ubuntu.com/ubuntu}
SUITES=${SUITES:-noble noble-updates}
PKG_LIMIT=${PKG_LIMIT:-0}
JOBS=${JOBS:-8}
mkdir -p "$CACHE/indexes" "$CACHE/debs"

echo "==> downloading indexes ($SUITES)"
for s in $SUITES; do
  curl -fsSL --retry 3 -o "$CACHE/indexes/Contents-$s.gz" "$MIRROR/dists/$s/Contents-amd64.gz"
  curl -fsSL --retry 3 -o "$CACHE/indexes/Packages-$s.gz" "$MIRROR/dists/$s/main/binary-amd64/Packages.gz"
done

echo "==> finding main packages that ship man pages"
for s in $SUITES; do zcat "$CACHE/indexes/Contents-$s.gz"; done \
  | awk '$1 ~ /^usr\/share\/man\/man[1-9]/ {
      n = split($NF, a, ",");
      for (i = 1; i <= n; i++) if (split(a[i], b, "/") == 2) print b[2];
    }' | sort -u > "$CACHE/manpkgs.txt"
echo "    packages: $(wc -l < "$CACHE/manpkgs.txt")"

echo "==> building download list (later suites override earlier)"
for s in $SUITES; do zcat "$CACHE/indexes/Packages-$s.gz"; done \
  | awk -v RS='' -F'\n' '{
      pkg = ""; fn = ""; sha = "";
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^Package: /)  pkg = substr($i, 10);
        if ($i ~ /^Filename: /) fn  = substr($i, 11);
        if ($i ~ /^SHA256: /)   sha = substr($i, 9);
      }
      if (pkg != "" && fn != "") print pkg "\t" fn "\t" sha;
    }' \
  | awk -F'\t' '{ m[$1] = $0 } END { for (k in m) print m[k] }' \
  | sort > "$CACHE/allpkgs.tsv"
join -t "$(printf '\t')" "$CACHE/manpkgs.txt" "$CACHE/allpkgs.tsv" > "$CACHE/download.tsv"
echo "    to download: $(wc -l < "$CACHE/download.tsv")"

LIST=$CACHE/download.tsv
if [ "$PKG_LIMIT" -gt 0 ]; then
  head -n "$PKG_LIMIT" "$LIST" > "$CACHE/download.limited.tsv"
  LIST=$CACHE/download.limited.tsv
fi

echo "==> downloading $(wc -l < "$LIST") debs with $JOBS jobs"
export MIRROR CACHE
dl() {
  local fn=$1 sha=$2 out
  out=$CACHE/debs/$(basename "$fn")
  [ -f "$out" ] && return 0
  if ! curl -fsSL --retry 3 -o "$out.tmp" "$MIRROR/$fn"; then
    echo "FETCH-FAIL $fn" >> "$CACHE/fetch-failures.log"; rm -f "$out.tmp"; return 0
  fi
  if ! echo "$sha  $out.tmp" | sha256sum -c --quiet - 2>/dev/null; then
    echo "SHA-FAIL $fn" >> "$CACHE/fetch-failures.log"; rm -f "$out.tmp"; return 0
  fi
  mv "$out.tmp" "$out"
}
export -f dl
: > "$CACHE/fetch-failures.log"
cut -f2,3 "$LIST" | xargs -P "$JOBS" -n 2 bash -c 'dl "$@"' _
echo "==> cached debs: $(ls "$CACHE/debs" | wc -l), failures: $(wc -l < "$CACHE/fetch-failures.log")"
