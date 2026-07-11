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
COMPONENTS=${COMPONENTS:-main universe}
PKG_LIMIT=${PKG_LIMIT:-0}
JOBS=${JOBS:-8}
mkdir -p "$CACHE/indexes" "$CACHE/debs"

echo "==> downloading indexes ($SUITES / $COMPONENTS)"
for s in $SUITES; do
  curl -fsSL --retry 3 -o "$CACHE/indexes/Contents-$s.gz" "$MIRROR/dists/$s/Contents-amd64.gz"
  for c in $COMPONENTS; do
    curl -fsSL --retry 3 -o "$CACHE/indexes/Packages-$s-$c.gz" "$MIRROR/dists/$s/$c/binary-amd64/Packages.gz"
  done
done

echo "==> finding packages that ship man pages ($COMPONENTS)"
for s in $SUITES; do zcat "$CACHE/indexes/Contents-$s.gz"; done \
  | awk -v comps="$COMPONENTS" '
    BEGIN { n = split(comps, cl, " "); for (i = 1; i <= n; i++) ok[cl[i]] = 1 }
    $1 ~ /^usr\/share\/man\/man[1-9]/ {
      m = split($NF, a, ",");
      for (i = 1; i <= m; i++) {
        k = split(a[i], b, "/");
        if (k == 2 && ok["main"]) print b[2];
        else if (k == 3 && ok[b[1]]) print b[3];
      }
    }' | sort -u > "$CACHE/manpkgs.txt"
echo "    packages: $(wc -l < "$CACHE/manpkgs.txt")"

echo "==> building download list (later suites override earlier)"
for s in $SUITES; do for c in $COMPONENTS; do zcat "$CACHE/indexes/Packages-$s-$c.gz"; done; done \
  | awk -v RS='' -F'\n' '{
      pkg = ""; fn = ""; sha = ""; sz = 0;
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^Package: /)  pkg = substr($i, 10);
        if ($i ~ /^Filename: /) fn  = substr($i, 11);
        if ($i ~ /^SHA256: /)   sha = substr($i, 9);
        if ($i ~ /^Size: /)     sz  = substr($i, 7);
      }
      if (pkg != "" && fn != "") print pkg "\t" fn "\t" sha "\t" sz;
    }' \
  | awk -F'\t' '{ m[$1] = $0 } END { for (k in m) print m[k] }' \
  | sort > "$CACHE/allpkgs.tsv"
join -t "$(printf '\t')" "$CACHE/manpkgs.txt" "$CACHE/allpkgs.tsv" > "$CACHE/download.tsv"
echo "    to download: $(wc -l < "$CACHE/download.tsv")"
awk -F'\t' '{ s += $4 } END { printf "    total download size: %.1f GB\n", s / 1e9 }' "$CACHE/download.tsv"
if [ "${INDEX_ONLY:-0}" = "1" ]; then echo "==> INDEX_ONLY=1, stopping before downloads"; exit 0; fi

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
