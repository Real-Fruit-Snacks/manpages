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
HEADFOOT_B_RE = re.compile(rb'<table class="(?:head|foot)">.*?</table>', re.S)
HREF_RE = re.compile(r'href="\.\./([^"#]+)"')
REL_A_RE = re.compile(r'<a\b[^>]*href="\.\./(?!\.\./)([^"#]+)"[^>]*>(.*?)</a>', re.S)


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


def unwrap_noncorpus_links(content, planned):
    """Unwrap <a> tags whose ../-relative target is not a page we will write
    (e.g. stray relative links in upstream roff sources)."""
    def repl(m):
        return m.group(0) if m.group(1) in planned else m.group(2)
    return REL_A_RE.sub(repl, content)


def extract_toc(content):
    toc = []
    for m in H_RE.finditer(content):
        label = TAG_RE.sub('', m.group(2)).strip()
        if label:
            toc.append((m.group(1), label))
    return toc


SECTION_NAMES = {
    '1': 'User commands', '2': 'System calls', '3': 'Library functions',
    '4': 'Devices & special files', '5': 'File formats', '6': 'Games',
    '7': 'Overviews & conventions', '8': 'System administration', '9': 'Kernel',
}


def chunk_entries(entries, limit=2000):
    """Pack alphabetically-sorted entries into <=limit chunks along letter
    boundaries. entries: sequence of tuples whose [0] is the sort name.
    Returns [(label, [entries])] with labels like 'a' or 'b–c'."""
    groups = []
    for e in entries:
        ch = (e[0][:1] or '#').lower()
        if groups and groups[-1][0] == ch:
            groups[-1][1].append(e)
        else:
            groups.append((ch, [e]))
    chunks = []
    cur_lo = cur_hi = None
    cur = []
    for ch, items in groups:
        if cur and len(cur) + len(items) > limit:
            chunks.append((cur_lo if cur_lo == cur_hi else '%s–%s' % (cur_lo, cur_hi), cur))
            cur, cur_lo = [], None
        cur.extend(items)
        cur_lo = cur_lo or ch
        cur_hi = ch
    if cur:
        chunks.append((cur_lo if cur_lo == cur_hi else '%s–%s' % (cur_lo, cur_hi), cur))
    return chunks


def write_listings(pages, out, tpl):
    by_sect = {}
    for p in pages:
        by_sect.setdefault(p['sect'], []).append(p)
    browse_dir = os.path.join(out, 'browse')
    os.makedirs(browse_dir, exist_ok=True)
    sect_links = []
    for sect in sorted(by_sect, key=lambda s: (s[0], s)):
        entries = sorted(by_sect[sect], key=lambda p: p['name'].lower())
        chunks = chunk_entries([(p['name'], p) for p in entries])
        files = []
        for n, (label, items) in enumerate(chunks):
            fname = '%s.html' % sect if len(chunks) == 1 else '%s-%d.html' % (sect, n + 1)
            body = ['<h1 class="Sh">section %s — %s%s</h1>' % (
                html.escape(sect), html.escape(SECTION_NAMES.get(sect[0], '')),
                '' if len(chunks) == 1 else ' (%s)' % html.escape(label))]
            body.append('<ul class="listing-list">')
            for _, p in items:
                body.append('<li><a href="../%s">%s(%s)</a> <span class="l-desc">%s</span></li>'
                            % (p['path'], html.escape(p['name']),
                               html.escape(p['sect']), html.escape(p['desc'])))
            body.append('</ul>')
            with open(os.path.join(browse_dir, fname), 'w', encoding='utf-8') as f:
                f.write(tpl.replace('{root}', '../')
                        .replace('{title}', html.escape('section %s%s' % (
                            sect, '' if len(chunks) == 1 else ' ' + label)))
                        .replace('{content}', '\n'.join(body)))
            files.append((fname, label))
        sect_links.append((sect, len(entries), files))
    idx = ['<h1 class="Sh">browse by section</h1><ul class="listing-list listing-sections">']
    for sect, count, files in sect_links:
        if len(files) > 1:
            links = ' '.join('<a href="%s">%s</a>' % (html.escape(f), html.escape(l))
                             for f, l in files)
        else:
            links = '<a href="%s">all</a>' % html.escape(files[0][0])
        idx.append('<li><b>man%s</b> — %s <span class="l-desc">%d pages</span> · %s</li>'
                   % (html.escape(sect), html.escape(SECTION_NAMES.get(sect[0], '')),
                      count, links))
    idx.append('</ul>')
    with open(os.path.join(browse_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(tpl.replace('{root}', '../').replace('{title}', 'browse')
                .replace('{content}', '\n'.join(idx)))


def write_about(pages, n_aliases, out, tpl, gen_date):
    body = ('<h1 class="Sh">about</h1>\n'
            '<p>Offline Linux manual: %d man pages (%d aliases) pre-rendered from\n'
            'Ubuntu 24.04 LTS (noble + noble-updates, main + universe, amd64),\n'
            'snapshot %s.</p>\n'
            '<p>Everything is static and self-contained: no CDNs, no external fonts,\n'
            'no analytics, no network calls. Works from GitHub/GitLab Pages, any web\n'
            'server, or straight off disk.</p>\n'
            '<h1 class="Sh">licenses</h1>\n'
            '<p>Site tooling: MIT. Man page content: upstream Ubuntu package licenses\n'
            '(see each page footer for its source package). Theme:\n'
            'terminal-workbench-design-system (MIT). Font: JetBrains Mono (OFL 1.1).</p>'
            % (len(pages), n_aliases, gen_date))
    with open(os.path.join(out, 'about.html'), 'w', encoding='utf-8') as f:
        f.write(tpl.replace('{root}', './').replace('{title}', 'about')
                .replace('{content}', body))


def parse_page_rows(lines):
    """pages.tsv rows: name, sect, relpath[, source-tree key]. Pad to 4."""
    rows = []
    for line in lines:
        line = line.rstrip('\n')
        if not line:
            continue
        parts = line.split('\t', 3)
        if len(parts) == 3:
            parts.append('')
        if len(parts) == 4:
            rows.append(tuple(parts))
    return rows


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
    ap.add_argument('--pkg-components', default='',
                    help='tsv of package<TAB>component (from fetch.sh)')
    ap.add_argument('--drop', default='',
                    help='component:sections to exclude, e.g. universe:2,3,4,9')
    args = ap.parse_args()
    work, out = args.work, args.out

    with open(os.path.join(work, 'pages.tsv'), encoding='utf-8', errors='replace') as f:
        page_rows = parse_page_rows(f)
    alias_rows = load_tsv(os.path.join(work, 'aliases.tsv'), 4)
    filemap = dict((r[0], (r[1], r[2]))
                   for r in load_tsv(os.path.join(work, 'filemap.tsv'), 3))
    desc_rows = load_tsv(os.path.join(work, 'descriptions.tsv'), 3)
    methods = dict((r[0], r[1]) for r in load_tsv(os.path.join(work, 'convert-report.tsv'), 2))
    descs = dict(((n, s), d) for n, s, d in desc_rows)

    compmap = dict((r[0], r[1]) for r in load_tsv(args.pkg_components, 2)) \
        if args.pkg_components else {}
    drop_comp, drop_sects = '', set()
    if args.drop:
        drop_comp, _, sects = args.drop.partition(':')
        drop_sects = set(s.strip() for s in sects.split(',') if s.strip())

    report = []
    pages = []
    taken_by_dir = {}
    seen = set()
    n_dropped = 0
    for name, sect, relsrc, src_key in sorted(page_rows):
        if (name, sect) in seen:
            continue
        seen.add((name, sect))
        if drop_sects and sect[:1] in drop_sects:
            fm_entry = filemap.get(src_key)
            if fm_entry and compmap.get(fm_entry[0], '') == drop_comp:
                n_dropped += 1
                continue
        src = os.path.join(work, 'html', relsrc + '.html')
        if not os.path.exists(src):
            report.append('MISSING-HTML %s' % relsrc)
            continue
        slug = slugify(name, taken_by_dir.setdefault(sect, {}))
        pages.append({'name': name, 'sect': sect, 'slug': slug, 'src': src,
                      'desc': descs.get((name, sect), ''),
                      'method': methods.get(relsrc, 'mandoc'),
                      'src_key': src_key,
                      'path': 'man/%s/%s.html' % (sect, slug)})

    # Content dedupe: pages whose body (minus their own head/foot tables) is
    # identical become aliases of one canonical page. Collapses e.g. the ~2 MB
    # GCC manual duplicated across every cross-compiler triplet.
    body_hash = {}
    unique_pages = []
    dup_aliases = []
    n_dup_bytes = 0
    for p in pages:
        with open(p['src'], 'rb') as f:
            raw = f.read()
        h = hashlib.md5(HEADFOOT_B_RE.sub(b'', raw)).hexdigest() if len(raw) > 65536 \
            else None  # only dedupe large pages; small dupes aren't worth aliasing
        if h and h in body_hash:
            dup_aliases.append((p['name'], p['sect'], body_hash[h]))
            n_dup_bytes += len(raw)
            continue
        if h:
            body_hash[h] = p
        unique_pages.append(p)
    if dup_aliases:
        report.append('DEDUPED %d pages (%.1f MB) into aliases'
                      % (len(dup_aliases), n_dup_bytes / 1e6))
    pages = unique_pages

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
    for a, asec, target_page in dup_aliases:
        idx = index_of.get((target_page['name'], target_page['sect']))
        if idx is not None and (a, asec) not in index_of:
            alias_entries.append([a, asec, idx])

    tpl_path = os.path.join(args.templates, 'page.html')
    with open(tpl_path, encoding='utf-8') as f:
        tpl = f.read()
    gen_date = datetime.date.today().isoformat()

    n_pre = 0
    internal_hrefs = set()
    written = set()
    planned = set('%s/%s.html' % (p['sect'], p['slug']) for p in pages)
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
        content = unwrap_noncorpus_links(content, planned)
        toc_html = ''.join(
            '<li><a href="#%s">%s</a></li>' % (html.escape(i, quote=True), html.escape(t))
            for i, t in extract_toc(content))
        pkg = filemap.get(p.get('src_key', ''))
        source_html = ('source: %s %s · ' % (html.escape(pkg[0]), html.escape(pkg[1]))) if pkg else ''
        page_html = (tpl
                     .replace('{root}', '../../')
                     .replace('{source}', source_html)
                     .replace('{title}', html.escape('%s(%s)' % (p['name'], p['sect'])))
                     .replace('{desc}', html.escape(p['desc'], quote=True))
                     .replace('{generated}', gen_date)
                     .replace('{toc}', toc_html)
                     .replace('{content}', content))
        for m in HREF_RE.finditer(content):
            internal_hrefs.add(m.group(1))
        if '<img' in content:
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

    # Service worker: version = date + index hash so corpus refreshes bust caches.
    with open(os.path.join(out, 'data', 'index.js'), 'rb') as f:
        idx_hash = hashlib.md5(f.read()).hexdigest()[:8]
    listing_tpl_path = os.path.join(args.templates, 'listing.html')
    if os.path.exists(listing_tpl_path):
        with open(listing_tpl_path, encoding='utf-8') as f:
            listing_tpl = f.read()
        write_listings(pages, out, listing_tpl)
        write_about(pages, len(alias_entries), out, listing_tpl, gen_date)

    sw_tpl_path = os.path.join(args.templates, 'sw.js')
    if os.path.exists(sw_tpl_path):
        with open(sw_tpl_path, encoding='utf-8') as f:
            sw = f.read().replace('{version}', '%s-%s' % (gen_date, idx_hash))
        with open(os.path.join(out, 'sw.js'), 'w', encoding='utf-8') as f:
            f.write(sw)

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

    print('pages=%d aliases=%d pre=%d(%.2f%%) dropped=%d notes=%d errors=%d'
          % (len(pages), len(alias_entries), n_pre, pct, n_dropped, len(report), len(errors)))
    if errors:
        for e in errors[:10]:
            print('ERROR', e, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
