#!/usr/bin/env python3
"""Spot-check 200 random generated pages for basic structure."""
import pathlib
import random
import re
import sys

docs = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'docs')
pages = list(docs.glob('man/*/*.html'))
if not pages:
    print('FAIL: no generated pages under', docs)
    sys.exit(1)
sample = random.sample(pages, min(200, len(pages)))
bad = []
for p in sample:
    t = p.read_text(encoding='utf-8', errors='replace')
    if '</html>' not in t or '<article' not in t:
        bad.append((p, 'broken structure'))
    elif not re.search(r'id="NAME"|>NAME<|class="plain-roff"', t):
        bad.append((p, 'no NAME section'))
print('checked %d of %d pages, %d bad' % (len(sample), len(pages), len(bad)))
for p, why in bad[:20]:
    print('  FAIL %s: %s' % (p, why))
sys.exit(1 if bad else 0)
