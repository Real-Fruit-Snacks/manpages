#!/usr/bin/env bash
# convert.sh — render every extracted page to HTML.
# Fallback chain per page: mandoc fragment -> groff full doc -> escaped <pre>.
#
# usage: convert.sh <workdir>   (a workdir produced by extract.sh)
set -euo pipefail
WORK=${1:?usage: convert.sh <workdir>}
WORK=$(readlink -f "$WORK")
HTML=$WORK/html
rm -rf "$HTML"; mkdir -p "$HTML"
: > "$WORK/convert-report.tsv"
export WORK HTML

conv_one() {
  local rel=$1 src=$WORK/pages/$1 out=$HTML/$1.html method=mandoc
  mkdir -p "${out%/*}"
  if ! timeout 30 mandoc -T html -O fragment,man=../%S/%N.html "$src" > "$out" 2>/dev/null || [ ! -s "$out" ]; then
    method=groff
    # grohtml renders complex tables/equations as PNG files dropped in cwd,
    # which would be dangling resources on the static site — treat as failure.
    if ! timeout 30 groff -mandoc -Thtml "$src" > "$out" 2>/dev/null || [ ! -s "$out" ] \
       || grep -q '<img' "$out"; then
      method=pre
      { printf '<pre class="plain-roff">'
        python3 -c 'import sys,html; sys.stdout.write(html.escape(sys.stdin.read()))' < "$src"
        printf '</pre>'
      } > "$out"
    fi
  fi
  printf '%s\t%s\n' "$rel" "$method" >> "$WORK/convert-report.tsv"
  return 0
}
export -f conv_one

cut -f3 "$WORK/pages.tsv" | xargs -P "$(nproc)" -n 1 bash -c 'conv_one "$1"' _
echo "==> converted: $(wc -l < "$WORK/convert-report.tsv") of $(wc -l < "$WORK/pages.tsv")"
awk -F'\t' '{ c[$2]++ } END { for (m in c) printf "    %s: %d\n", m, c[m] }' "$WORK/convert-report.tsv"
