#!/usr/bin/env bash
# extract.sh — collect canonical man pages, aliases (.so + symlinks), and
# one-line descriptions from a man tree.
#
# usage: extract.sh <man-root> <workdir>
#   <man-root>  directory containing man1..man9* (e.g. /usr/share/man)
#   <workdir>   output directory (created); produces pages/, pages.tsv,
#               aliases.tsv, descriptions.tsv, extract.log
set -euo pipefail
SRC=${1:?usage: extract.sh <man-root> <workdir>}
WORK=${2:?usage: extract.sh <man-root> <workdir>}
SRC=$(readlink -f "$SRC"); mkdir -p "$WORK"; WORK=$(readlink -f "$WORK")
PAGES=$WORK/pages
rm -rf "$PAGES"; mkdir -p "$PAGES"
: > "$WORK/pages.tsv"; : > "$WORK/aliases.tsv"; : > "$WORK/extract.log"

emit_alias() { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >> "$WORK/aliases.tsv"; }

split_target() { # sets tname/tsect from a path like ../man1/tar.1.gz
  local tbase=${1##*/} tstem
  tstem=${tbase%.gz}
  tsect=${tstem##*.}; tname=${tstem%.*}
}

shopt -s nullglob
for dir in "$SRC"/man[1-9]*; do
  for f in "$dir"/*; do
    base=${f##*/}
    stem=${base%.gz}
    sect=${stem##*.}
    name=${stem%.*}
    if [ "$name" = "$stem" ] || [ -z "$name" ]; then
      echo "SKIP no-section $f" >> "$WORK/extract.log"; continue
    fi
    case $name in *$'\t'*) echo "SKIP tab-in-name $f" >> "$WORK/extract.log"; continue;; esac
    if [ -L "$f" ]; then
      split_target "$(readlink "$f")"
      emit_alias "$name" "$sect" "$tname" "$tsect"
      continue
    fi
    [ -f "$f" ] || continue
    first=$(zcat -f "$f" 2>/dev/null | grep -m1 -v '^\.\\"' || true)
    case $first in
      .so\ *)
        split_target "${first#.so }"
        emit_alias "$name" "$sect" "$tname" "$tsect"
        continue;;
    esac
    outdir=$PAGES/$sect
    mkdir -p "$outdir"
    if [ -e "$outdir/$stem" ]; then
      echo "DUP $name.$sect ($f)" >> "$WORK/extract.log"; continue
    fi
    if ! zcat -f "$f" > "$outdir/$stem" 2>/dev/null; then
      rm -f "$outdir/$stem"; echo "READ-FAIL $f" >> "$WORK/extract.log"; continue
    fi
    printf '%s\t%s\t%s\t%s\n' "$name" "$sect" "$sect/$stem" "${dir##*/}/$base" >> "$WORK/pages.tsv"
  done
done
echo "==> pages: $(wc -l < "$WORK/pages.tsv"), aliases: $(wc -l < "$WORK/aliases.tsv"), log: $(wc -l < "$WORK/extract.log")"

# --- one-line descriptions via lexgrog, in parallel ---
: > "$WORK/descriptions.tsv"
export WORK
desc_one() {
  local rel=$1 sect=${1%%/*} stem line d
  stem=${rel##*/}
  local name=${stem%.*}
  line=$(lexgrog "$WORK/pages/$rel" 2>/dev/null | head -n1) || return 0
  d=${line#*: \"}; d=${d%\"}; d=${d#* - }
  [ -n "$d" ] && [ "$d" != "$line" ] && printf '%s\t%s\t%s\n' "$name" "$sect" "$d" >> "$WORK/descriptions.tsv"
  return 0
}
export -f desc_one
cut -f3 "$WORK/pages.tsv" | xargs -P "$(nproc)" -n 1 bash -c 'desc_one "$1"' _
echo "==> descriptions: $(wc -l < "$WORK/descriptions.tsv")"
