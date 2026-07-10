#!/usr/bin/env python3
"""Build the static site from a workdir produced by extract.sh + convert.sh.

Reads   <work>/pages.tsv, aliases.tsv, descriptions.tsv, convert-report.tsv, html/
Writes  <out>/man/<sect>/<slug>.html, <out>/data/index.js, <work>/site-report.txt
Exits non-zero if validation fails (missing files, dangling links, >max-fallback-pct
pages in the <pre> fallback).
"""
import argparse
import datetime
import hashlib
import html
import json
import os
import re
import sys

BAD_CHARS = re.compile(r'[:<>"\\|?*\s]')
XR_RE = re.compile(r'<a class="Xr"[^>]*>([^<]*)</a>')
REF_RE = re.compile(r'^([^()\s][^()]*)\((\w+)\)$')
H_RE = re.compile(r'<h[12][^>]*\bid="([^"]+)"[^>]*>(.*?)</h[12]>', re.S)
TAG_RE = re.compile(r'<[^>]+>')
BODY_RE = re.compile(r'<body[^>]*>(.*)</body>', re.S)
HREF_RE = re.compile(r'href="\.\./([^"#]+)"')


def slugify(name, taken):
    """NTFS/URL-safe slug, unique (case-insensitively) within one directory.

    taken: dict lowercased-slug -> original name, mutated per section dir.
    """
    slug = BAD_CHARS.sub('_', name)
    key = slug.lower()
    if key in taken and taken[key] != name:
        slug += '~' + hashlib.md5(name.encode('utf-8')).hexdigest()[:6]
        key = slug.lower()
    taken[key] = name
    return slug


def build_maps(pages):
    exact = {}
    by_base = {}
    for p in pages:
        exact[(p['name'], p['sect'])] = p
        k = (p['name'], p['sect'][0])
        if k not in by_base or len(p['sect']) < len(by_base[k]['sect']):
            by_base[k] = p
    return exact, by_base


def rewrite_xr(content, exact, by_base, alias_target):
    def repl(m):
        text = m.group(1).strip()
        ref = REF_RE.match(text)
        if ref:
            name, sect = ref.group(1).strip(), ref.group(2)
            p = (exact.get((name, sect)) or by_base.get((name, sect[0]))
                 or alias_target(name, sect))
            if p:
                return '<a class="Xr" href="../%s/%s.html">%s</a>' % (
                    p['sect'], p['slug'], html.escape(text))
        return '<span class="Xr">%s</span>' % html.escape(text)
    return XR_RE.sub(repl, content)


BOLD_REF_RE = re.compile(r'<([bi])>([A-Za-z0-9_.:+\-]+)</\1>\((\d\w{0,8})\)')


def linkify_refs(content, exact, by_base, alias_target):
    """Link man(7)-style references (.BR name (sect) -> <b>name</b>(sect)).

    Only mdoc pages produce <a class="Xr">; classic man pages render refs as
    bold/italic text. Section must start with a digit, which keeps function
    calls and ordinary parentheses out.
    """
    def repl(m):
        tag, name, sect = m.groups()
        p = (exact.get((name, sect)) or by_base.get((name, sect[0]))
             or alias_target(name, sect))
        if p:
            return '<a class="Xr" href="../%s/%s.html"><%s>%s</%s>(%s)</a>' % (
                p['sect'], p['slug'], tag, name, tag, sect)
        return m.group(0)
    return BOLD_REF_RE.sub(repl, content)


def extract_toc(content):
    toc = []
    for m in H_RE.finditer(content):
        label = TAG_RE.sub('', m.group(2)).strip()
        if label:
            toc.append((m.group(1), label))
    return toc


def load_tsv(path, ncols):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line:
                continue
            parts = line.split('\t', ncols - 1)
            if len(parts) == ncols:
                rows.append(parts)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--templates',
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
    ap.add_argument('--max-fallback-pct', type=float, default=2.0)
    args = ap.parse_args()
    work, out = args.work, args.out

    page_rows = load_tsv(os.path.join(work, 'pages.tsv'), 3)
    alias_rows = load_tsv(os.path.join(work, 'aliases.tsv'), 4)
    desc_rows = load_tsv(os.path.join(work, 'descriptions.tsv'), 3)
    methods = dict((r[0], r[1]) for r in load_tsv(os.path.join(work, 'convert-report.tsv'), 2))
    descs = dict(((n, s), d) for n, s, d in desc_rows)

    report = []
    pages = []
    taken_by_dir = {}
    seen = set()
    for name, sect, relsrc in sorted(page_rows):
        if (name, sect) in seen:
            continue
        seen.add((name, sect))
        src = os.path.join(work, 'html', relsrc + '.html')
        if not os.path.exists(src):
            report.append('MISSING-HTML %s' % relsrc)
            continue
        slug = slugify(name, taken_by_dir.setdefault(sect, {}))
        pages.append({'name': name, 'sect': sect, 'slug': slug, 'src': src,
                      'desc': descs.get((name, sect), ''),
                      'method': methods.get(relsrc, 'mandoc'),
                      'path': 'man/%s/%s.html' % (sect, slug)})

    exact, by_base = build_maps(pages)
    alias_map = dict(((a, asec), (t, tsec)) for a, asec, t, tsec in alias_rows)

    def alias_target(name, sect, _depth=8):
        key = (name, sect)
        for _ in range(_depth):
            if key not in alias_map:
                break
            key = alias_map[key]
            p = exact.get(key) or by_base.get((key[0], key[1][:1] or '?'))
            if p:
                return p
        return None

    index_of = dict(((p['name'], p['sect']), i) for i, p in enumerate(pages))
    alias_entries = []
    for a, asec, t, tsec in alias_rows:
        if (a, asec) in index_of:
            continue  # a real page shadows the alias
        p = exact.get((t, tsec)) or by_base.get((t, tsec[:1] or '?')) or alias_target(t, tsec)
        if p is None:
            report.append('DANGLING-ALIAS %s(%s) -> %s(%s)' % (a, asec, t, tsec))
            continue
        alias_entries.append([a, asec, index_of[(p['name'], p['sect'])]])

    tpl_path = os.path.join(args.templates, 'page.html')
    with open(tpl_path, encoding='utf-8') as f:
        tpl = f.read()
    gen_date = datetime.date.today().isoformat()

    n_pre = 0
    internal_hrefs = set()
    written = set()
    for p in pages:
        with open(p['src'], encoding='utf-8', errors='replace') as f:
            content = f.read()
        if p['method'] == 'groff':
            m = BODY_RE.search(content)
            if m:
                content = m.group(1)
        elif p['method'] == 'pre':
            n_pre += 1
        content = rewrite_xr(content, exact, by_base, alias_target)
        content = linkify_refs(content, exact, by_base, alias_target)
        toc_html = ''.join(
            '<li><a href="#%s">%s</a></li>' % (html.escape(i, quote=True), html.escape(t))
            for i, t in extract_toc(content))
        page_html = (tpl
                     .replace('{root}', '../../')
                     .replace('{title}', html.escape('%s(%s)' % (p['name'], p['sect'])))
                     .replace('{desc}', html.escape(p['desc'], quote=True))
                     .replace('{generated}', gen_date)
                     .replace('{toc}', toc_html)
                     .replace('{content}', content))
        for m in HREF_RE.finditer(content):
            internal_hrefs.add(m.group(1))
        if 'grohtml-' in content:
            report.append('GROHTML-IMG %s' % p['path'])
        dest = os.path.join(out, p['path'])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(page_html)
        written.add('%s/%s.html' % (p['sect'], p['slug']))

    db = {'v': 1, 'generated': gen_date,
          'pages': [[p['name'], p['sect'], p['desc'], p['path']] for p in pages],
          'aliases': alias_entries}
    os.makedirs(os.path.join(out, 'data'), exist_ok=True)
    with open(os.path.join(out, 'data', 'index.js'), 'w', encoding='utf-8') as f:
        f.write('window.MANDB=')
        f.write(json.dumps(db, ensure_ascii=False, separators=(',', ':')))
        f.write(';\n')

    # ---- validation ----
    errors = []
    for p in pages:
        if not os.path.exists(os.path.join(out, p['path'])):
            errors.append('index path missing: %s' % p['path'])
    for line in report:
        if line.startswith('GROHTML-IMG'):
            errors.append(line)
    dangling = internal_hrefs - written
    for d in sorted(dangling)[:20]:
        errors.append('dangling internal link: ../%s' % d)
    pct = (100.0 * n_pre / len(pages)) if pages else 0.0
    if pct > args.max_fallback_pct:
        errors.append('pre-fallback rate %.2f%% exceeds %.2f%%' % (pct, args.max_fallback_pct))

    with open(os.path.join(work, 'site-report.txt'), 'w', encoding='utf-8') as f:
        f.write('pages: %d\naliases: %d\npre-fallback: %d (%.2f%%)\n'
                % (len(pages), len(alias_entries), n_pre, pct))
        f.write('notes: %d\n' % len(report))
        for line in report[:200]:
            f.write('  %s\n' % line)
        for e in errors:
            f.write('ERROR %s\n' % e)

    print('pages=%d aliases=%d pre=%d(%.2f%%) notes=%d errors=%d'
          % (len(pages), len(alias_entries), n_pre, pct, len(report), len(errors)))
    if errors:
        for e in errors[:10]:
            print('ERROR', e, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
