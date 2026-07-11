#!/usr/bin/env python3
"""Audit generated pages: internal links resolve, no <img>, assets exist.

usage: audit_links.py <docs-dir> [--sample N]   (N=0 means all pages)
"""
import argparse
import pathlib
import random
import re
import sys

MAN_RE = re.compile(r'href="\.\./(?!\.\./)([^"#]+)"')   # ../sect/page.html cross-refs
ROOT_RE = re.compile(r'href="\.\./\.\./([^"#]+)"')       # shell chrome to site root
SRC_RE = re.compile(r'src="(?:\.\./)*((?:assets|data)/[^"?#]+)"')
IMG_RE = re.compile(r'<img\b')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('docs')
    ap.add_argument('--sample', type=int, default=0)
    args = ap.parse_args()
    docs = pathlib.Path(args.docs)
    man = docs / 'man'
    pages = sorted(man.glob('*/*.html'))
    if not pages:
        print('FAIL: no pages under', man)
        return 1
    sample = pages if not args.sample else random.sample(pages, min(args.sample, len(pages)))
    existing = set(p.relative_to(man).as_posix() for p in pages)
    errors = []
    for p in sample:
        t = p.read_text(encoding='utf-8', errors='replace')
        if IMG_RE.search(t):
            errors.append('%s: contains <img>' % p)
        for m in MAN_RE.finditer(t):
            if m.group(1) not in existing:
                errors.append('%s: dangling link ../%s' % (p, m.group(1)))
        for m in ROOT_RE.finditer(t):
            if not (docs / m.group(1)).exists():
                errors.append('%s: missing root file %s' % (p, m.group(1)))
        for m in SRC_RE.finditer(t):
            if not (docs / m.group(1)).exists():
                errors.append('%s: missing asset %s' % (p, m.group(1)))
    print('audited %d of %d pages: %d errors' % (len(sample), len(pages), len(errors)))
    for e in errors[:30]:
        print(' ', e)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
