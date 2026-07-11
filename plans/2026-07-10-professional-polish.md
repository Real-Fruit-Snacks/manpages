# Professional Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the manpages site into a professional application: universe corpus, package provenance, browse/about pages, accessible search, PWA/offline caching, print styles, search power features, recently-viewed, CI, LICENSE, CHANGELOG, tag-driven releases, README screenshots.

**Architecture:** All client/template/pipeline changes land first (Tasks 1–11), then one expensive full rebuild with `main`+`universe` captures everything (Task 12), then docs/screenshots and a single v1.2.0 release (Tasks 13–14).

**Tech Stack:** unchanged — bash + python stdlib (WSL Ubuntu-22.04), vanilla JS/CSS, mandoc. New: GitHub Actions CI, service worker, pure-python PNG icon writer.

## Global Constraints

- Zero network calls on the published site; all assets relative; works on `file://` (service worker must no-op there).
- Corpus: Ubuntu 24.04 LTS (`noble` + `noble-updates`), components **main + universe**, amd64, English, sections 1–9.
- Build aborts if >2% of pages hit the `<pre>` fallback; no generated-image (`grohtml-`) references may ship.
- NTFS-safe output filenames (existing `slugify`).
- WSL commands with variables/quotes go in script files (never inline `wsl.exe bash -c` with `$vars`); never edit a `.sh` while a WSL process is executing it.
- Repo path: `C:\Users\Matt\Documents\manpages` = `/mnt/c/Users/Matt/Documents/manpages` (`$REPO`); heavy I/O in `$HOME/manbuild`.
- localStorage keys keep the `twb-` prefix. Pet behavior/settings unchanged by this plan.
- All commits authored by Real-Fruit-Snacks; no AI attributions anywhere.
- After Task 12, `docs/data/index.js` may reach ~6 MB raw; that is accepted (still <2 s on first load, cached after).

---

### Task 1: LICENSE + CHANGELOG

**Files:**
- Create: `LICENSE`, `CHANGELOG.md`

**Interfaces:**
- Produces: `CHANGELOG.md` with an `## [Unreleased]` section that Task 14 renames to `## [1.2.0]` and the release workflow (Task 3) extracts notes from.

- [ ] **Step 1: Write `LICENSE`** — MIT, exact text:

```
MIT License

Copyright (c) 2026 Real-Fruit-Snacks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Note: this licenses the repo's own code/tooling. Man-page content remains under its upstream package licenses (already stated in README).

- [ ] **Step 2: Write `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to this project are documented here. Release assets: each
release attaches `manpages-site.zip`, the complete static site.

## [Unreleased]

## [1.1.2] - 2026-07-10
- Prompt character moved inside the search box so the dropdown aligns with the input.
- Ghost speech bubbles on by default.

## [1.1.1] - 2026-07-10
- Removed the home-page hero subtitle line.

## [1.1.0] - 2026-07-10
- Ghost pet companion (ported from Real-Fruit-Snacks/vault) with full settings:
  mode, size, opacity, six colors, behavior toggles.

## [1.0.2] - 2026-07-10
- Themed scrollbars everywhere (dark + light), theme-color metas, wide-table
  horizontal scrolling, light-mode 404 polish.

## [1.0.1] - 2026-07-10
- Fixed the search dropdown rendering detached below the hero input.
- Real favicon files (svg + ico); repository topics.
- Build rejects groff HTML that references generated images.

## [1.0.0] - 2026-07-10
- Initial release: 20,449 pre-rendered Ubuntu 24.04 (main) man pages,
  instant offline search, terminal-workbench theme, GitHub/GitLab Pages ready.
```

- [ ] **Step 3: Commit**

```
git add LICENSE CHANGELOG.md
git commit -m "chore: add MIT license and changelog"
```

---

### Task 2: Link audit script + CI workflow

**Files:**
- Create: `build/audit_links.py`, `.github/workflows/ci.yml`

**Interfaces:**
- Produces: `python3 build/audit_links.py docs [--sample N]` → exit 0/1. Checks every sampled page's internal `href="../..."` targets, `img` tags (none allowed except none), and that referenced `assets/` files exist. Used by CI and Task 14.
- CI runs the whole existing suite on every push/PR.

- [ ] **Step 1: Write `build/audit_links.py`**

```python
#!/usr/bin/env python3
"""Audit generated pages: internal links resolve, no <img>, assets exist.

usage: audit_links.py <docs-dir> [--sample N]   (N=0 means all pages)
"""
import argparse
import pathlib
import random
import re
import sys

HREF_RE = re.compile(r'href="\.\./([^"#]+)"')
ASSET_RE = re.compile(r'(?:src|href)="(?:\.\./)*((?:assets|data)/[^"?#]+)"')
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
        for m in HREF_RE.finditer(t):
            if m.group(1) not in existing:
                errors.append('%s: dangling link ../%s' % (p, m.group(1)))
        for m in ASSET_RE.finditer(t):
            if not (docs / m.group(1)).exists():
                errors.append('%s: missing asset %s' % (p, m.group(1)))
    print('audited %d of %d pages: %d errors' % (len(sample), len(pages), len(errors)))
    for e in errors[:30]:
        print(' ', e)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 2: Run it locally** (WSL): `python3 build/audit_links.py docs --sample 2000`
Expected: `audited 2000 ... 0 errors`, exit 0.

- [ ] **Step 3: Write `.github/workflows/ci.yml`**

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: search-core unit tests
        run: node build/test_search.js
      - name: build_site unit tests
        run: cd build && python3 -m unittest test_build_site -v
      - name: smoke test generated site
        run: python3 build/smoke_test.py docs
      - name: link audit (sampled)
        run: python3 build/audit_links.py docs --sample 2000
```

- [ ] **Step 4: Commit**

```
git add build/audit_links.py .github/workflows/ci.yml
git commit -m "ci: test suite and link audit on every push"
```

---

### Task 3: Tag-driven release automation

**Files:**
- Create: `.github/workflows/release.yml`
- Delete: `.github/workflows/release-zip.yml` (superseded)
- Modify: `README.md` (release instructions)

**Interfaces:**
- Pushing a tag `v*` builds `manpages-site.zip` from `docs/` and creates a Release whose body is that version's CHANGELOG section. Task 14 uses this instead of manual `gh release create`.

- [ ] **Step 1: Write `.github/workflows/release.yml`**

```yaml
name: release
on:
  push:
    tags: ['v*']
permissions:
  contents: write
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: build site zip
        run: cd docs && zip -qr ../manpages-site.zip .
      - name: extract changelog section
        run: |
          ver="${GITHUB_REF_NAME#v}"
          awk -v ver="$ver" '
            $0 ~ "^## \\[" ver "\\]" { on=1; next }
            on && /^## \[/ { exit }
            on { print }' CHANGELOG.md > notes.md
          if ! [ -s notes.md ]; then echo "No changelog entry for $ver" > notes.md; fi
          printf '\n**manpages-site.zip** is the complete static site: unzip and open index.html, or serve the folder anywhere.\n' >> notes.md
      - name: create release
        run: gh release create "$GITHUB_REF_NAME" manpages-site.zip --title "manpages $GITHUB_REF_NAME" --notes-file notes.md
        env:
          GH_TOKEN: ${{ github.token }}
```

- [ ] **Step 2: Delete `release-zip.yml`**, update README's refresh section to mention: releases are cut by pushing a tag (`git tag v1.2.0 && git push origin v1.2.0`).

- [ ] **Step 3: Commit**

```
git add -A .github README.md
git commit -m "ci: tag-driven releases with changelog notes"
```

---

### Task 4: Search section-filter syntax (TDD)

**Files:**
- Modify: `docs/assets/search-core.js`
- Test: `build/test_search.js`

**Interfaces:**
- `SearchCore.search` gains: a token matching `/^\d[a-z0-9]{0,5}$/i` acts as a section filter (`tar 5`, `5 tar`); a single token `name.SECT` where SECT starts with a digit splits (`tar.5`); a filter with no other tokens lists that whole section alphabetically. Filter matches sections by prefix (`3` matches `3ssl`). Every result gains `hl: [start, len] | null` — the first name-substring match, for highlighting (consumed by Task 5).

- [ ] **Step 1: Add failing tests to `build/test_search.js`** (append before the final console.log; also add a `tar(5)` page to the fixture `pages` array: `['tar', '5', 'format of tape archive files', 'man/5/tar2.html']` — note the distinct path so dedupe keeps both):

```js
r = SearchCore.search(db, 'tar 5', 10);
assert.strictEqual(r.length, 1, 'section filter narrows');
assert.strictEqual(r[0].section, '5', 'tar 5 -> section 5');

r = SearchCore.search(db, '5 tar', 10);
assert.strictEqual(r[0].section, '5', 'filter position free');

r = SearchCore.search(db, 'tar.5', 10);
assert.strictEqual(r[0].section, '5', 'dot syntax splits');

r = SearchCore.search(db, 'e2fsck.conf', 10);
assert.strictEqual(r.length, 0, 'dot only splits when suffix starts with a digit');

r = SearchCore.search(db, '5', 10);
assert.ok(r.length >= 2 && r.every(function (x) { return x.section === '5'; }),
  'bare section lists the section');

r = SearchCore.search(db, 'tar', 10);
assert.deepStrictEqual(r[0].hl, [0, 3], 'exact match highlight span');
r = SearchCore.search(db, 'get', 10);
assert.deepStrictEqual(r.filter(function(x){return x.name==='target';})[0].hl, [3, 3],
  'substring highlight offset');
r = SearchCore.search(db, 'archiving', 10);
assert.strictEqual(r[0].hl, null, 'description-only match has no name highlight');
```

- [ ] **Step 2: Run — expect failures.**

- [ ] **Step 3: Implement in `search-core.js`.** Replace the token setup and page loop head with:

```js
    var tokens = q.split(/\s+/);
    var sectFilter = null;
    var SECT_RE = /^\d[a-z0-9]{0,5}$/;
    if (tokens.length === 1) {
      var dm = tokens[0].match(/^(.+)\.(\d[a-z0-9]{0,5})$/);
      if (dm) { tokens = [dm[1]]; sectFilter = dm[2]; }
    }
    if (!sectFilter) {
      for (t = tokens.length - 1; t >= 0; t--) {
        if (tokens.length > 1 && SECT_RE.test(tokens[t])) {
          sectFilter = tokens[t]; tokens.splice(t, 1); break;
        }
      }
    }
    if (!sectFilter && tokens.length === 1 && SECT_RE.test(tokens[0])) {
      sectFilter = tokens[0]; tokens = [];
    }

    for (i = 0; i < pages.length; i++) {
      if (sectFilter && pages[i][1].toLowerCase().indexOf(sectFilter) !== 0) continue;
      var name = pages[i][0].toLowerCase();
      var desc = (pages[i][2] || '').toLowerCase();
      var total = 0, ok = true, hl = null;
      if (!tokens.length) { total = 1; }         /* bare-section listing */
      for (t = 0; t < tokens.length; t++) {
        s = scoreName(name, tokens[t]);
        if (s && !hl) hl = [name.indexOf(tokens[t]), tokens[t].length];
        if (!s && desc.indexOf(tokens[t]) !== -1) s = 30;
        if (!s) { ok = false; break; }
        total += s;
      }
      if (ok) results.push({ name: pages[i][0], section: pages[i][1],
        desc: pages[i][2] || '', path: pages[i][3], score: total, hl: hl });
    }
```

Alias loop: skip aliases entirely when `tokens.length === 0`; apply the same `sectFilter` prefix test against the alias's own section; alias results get `hl: null`. Bare-section listing sorts alphabetically already via the existing tiebreaker (equal scores).

- [ ] **Step 4: Run tests — all pass.** Also re-run existing assertions (fixture gained tar(5): the `'tar', 10` dedupe/order assertions still hold — verify).

- [ ] **Step 5: Commit** `feat: section filter syntax and highlight spans in search core`

---

### Task 5: Result highlighting (uses Task 4's `hl`)

**Files:**
- Modify: `docs/assets/app.js` (render), `docs/assets/app.css`

- [ ] **Step 1: In `app.js` `render()`, replace the name span construction with:**

```js
      var nameHtml;
      if (r.hl) {
        nameHtml = esc(r.name.slice(0, r.hl[0])) + '<mark>' +
          esc(r.name.slice(r.hl[0], r.hl[0] + r.hl[1])) + '</mark>' +
          esc(r.name.slice(r.hl[0] + r.hl[1]));
      } else {
        nameHtml = esc(r.name);
      }
      h += '<li id="opt-' + i + '" role="option" aria-selected="' + (i === sel) + '" class="' + (i === sel ? 'sel' : '') + '">' +
        '<a href="' + esc(root + r.path) + '">' +
        '<span class="r-name">' + nameHtml + '</span>' +
```

(The `id`/`role`/`aria-selected` attributes are consumed by Task 7 — adding them here avoids touching this string twice.)

- [ ] **Step 2: `app.css`:**

```css
.r-name mark { background: var(--twb-highlight); color: inherit; border-radius: 2px; }
```

- [ ] **Step 3: Browser verify** — type `tar`, the "tar" letters in results are tinted; type `tar 5` → only section-5 results; `5` alone lists section 5.

- [ ] **Step 4: Commit** `feat: match highlighting and section-filter UI`

---

### Task 6: Recently viewed

**Files:**
- Modify: `docs/assets/app.js`, `docs/index.html`, `docs/assets/app.css`

**Interfaces:**
- localStorage `twb-recent`: JSON array of `{t: "tar(1)", p: "man/1/tar.html"}`, newest first, deduped by `p`, max 8. Written on every man-page visit; rendered on the home page.

- [ ] **Step 1: Append a third IIFE to `app.js`:**

```js
/* Recently viewed: recorded on man pages, rendered on the home page. */
(function () {
  'use strict';
  var root = document.documentElement.getAttribute('data-root') || './';
  var KEY = 'twb-recent', MAX = 8;
  function load() {
    try { var v = JSON.parse(localStorage.getItem(KEY)); return Array.isArray(v) ? v : []; }
    catch (e) { return []; }
  }
  var m = location.pathname.match(/man\/([^/]+)\/([^/]+)\.html$/);
  if (m && document.querySelector('article.man-content')) {
    var entry = { t: document.title.replace(/\s+—.*$/, ''), p: 'man/' + m[1] + '/' + m[2] + '.html' };
    var list = load().filter(function (e) { return e.p !== entry.p; });
    list.unshift(entry);
    try { localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX))); } catch (e) { /* private mode */ }
  }
  var box = document.getElementById('recent');
  if (!box) return;
  var recent = load();
  if (!recent.length) return;
  var h = '<span class="recent-label">recent:</span>';
  for (var i = 0; i < recent.length; i++) {
    h += '<a class="recent-chip" href="' + root + recent[i].p.replace(/"/g, '') + '">' +
      recent[i].t.replace(/[&<>"]/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
      }) + '</a>';
  }
  box.innerHTML = h;
  box.hidden = false;
})();
```

- [ ] **Step 2: `index.html`** — after the `.hints` paragraph add: `<p id="recent" class="recent" hidden></p>`

- [ ] **Step 3: `app.css`:**

```css
.recent { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; max-width: 640px; justify-content: center; }
.recent-label { color: var(--twb-text-faint); font-size: 12px; }
.recent-chip {
  font-size: 12px; padding: 2px 10px; color: var(--twb-text-soft);
  background: var(--twb-tag-bg); border: 1px solid var(--twb-tag-border);
  border-radius: var(--twb-radius-pill);
}
.recent-chip:hover { color: var(--twb-accent); text-decoration: none; border-color: var(--twb-accent); }
```

- [ ] **Step 4: Browser verify** — visit tar(1) and grep(1), return home, chips appear newest-first; click works; `localStorage.twb-recent` capped.

- [ ] **Step 5: Commit** `feat: recently viewed chips on home page`

---

### Task 7: Accessible search (ARIA combobox)

**Files:**
- Modify: `build/templates/page.html`, `docs/index.html`, `docs/assets/app.js`, `docs/assets/app.css`

**Interfaces:**
- Input: `role="combobox" aria-expanded aria-controls="results" aria-autocomplete="list" aria-activedescendant`; list: `role="listbox"`; options carry `role="option" id="opt-N" aria-selected` (already emitted by Task 5). Man pages gain a skip link targeting `#content`.

- [ ] **Step 1: Markup (template AND index.html)** — search input becomes:

```html
<input id="search" type="search" role="combobox" aria-expanded="false" aria-controls="results" aria-autocomplete="list" aria-label="Search man pages" placeholder="search man pages" autocomplete="off" spellcheck="false">
<ul id="results" role="listbox" aria-label="Search results" hidden></ul>
```

(Template keeps its `( / )` placeholder variant.) Template only: as the first element inside `<body>` add `<a class="skip-link" href="#content">skip to content</a>` and change `<article class="man-content">` to `<article class="man-content" id="content">`.

- [ ] **Step 2: `app.js`** — in `render()` add after `list.hidden = false;`:

```js
    input.setAttribute('aria-expanded', String(!list.hidden && items.length > 0));
    if (sel >= 0) input.setAttribute('aria-activedescendant', 'opt-' + sel);
    else input.removeAttribute('aria-activedescendant');
```

and in the empty branch (`items.length === 0`) add `input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant');`. Same when the document-click handler hides the list.

- [ ] **Step 3: `app.css`:**

```css
.skip-link {
  position: absolute; left: -9999px; top: 0; z-index: 100;
  padding: 8px 14px; background: var(--twb-bg-2); color: var(--twb-accent);
  border: 1px solid var(--twb-accent); border-radius: var(--twb-radius-s);
}
.skip-link:focus { left: 8px; top: 8px; }
```

- [ ] **Step 4: Verify with the accessibility tree** (`read_page`): input reported as combobox with expanded state; options exposed; arrow keys move `aria-activedescendant`. Skip link appears on Tab and jumps to content.

- [ ] **Step 5: Commit** `a11y: combobox semantics for search, skip link on pages`

---

### Task 8: Print stylesheet

**Files:**
- Modify: `docs/assets/app.css`

- [ ] **Step 1: Append:**

```css
@media print {
  .site-header, .toc, #results, #theme-toggle, #pet-open, #pet-panel,
  #site-pet, .hints, .recent, .skip-link { display: none !important; }
  body { background: #fff; color: #000; font-size: 10.5pt; }
  .page { display: block; max-width: none; padding: 0; }
  .man-content { max-width: none; }
  .man-content h1, .man-content h1.Sh { color: #000; }
  .man-content pre, .man-content .Bd-indent { background: #fff; border: 1px solid #888; }
  a, .man-content a.Xr { color: #000; text-decoration: none; }
}
```

- [ ] **Step 2: Verify** — WSL has no headless Chrome; on the Windows side run Edge headless to render a PDF and confirm it is text-only (no header/ghost):
`& "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe" --headless=new --disable-gpu --print-to-pdf="$env:TEMP\tar.pdf" http://localhost:8321/man/1/tar.html` then open the PDF with Read and check page 1 starts with the page content, not the site header. (If Edge is missing, fall back to visual review of the rules.)

- [ ] **Step 3: Commit** `feat: print stylesheet`

---

### Task 9: PWA — icons, manifest, service worker

**Files:**
- Modify: `build/make_favicon.py` (expose `pixel()`/`SIZE`), `build/build_site.py` (stamp sw version), `build/templates/page.html`, `docs/index.html`
- Create: `build/make_icons.py`, `docs/manifest.webmanifest`, `build/templates/sw.js`, generated `docs/sw.js`, `docs/assets/icon-192.png`, `docs/assets/icon-512.png`

**Interfaces:**
- `sw.js` template placeholder `{version}` → build_site writes `docs/sw.js` with version = `<gen_date>-<first 8 hex of md5(index.js)>` so every corpus refresh invalidates caches.
- Registration snippet (template + index.html, before `</body>`): registers `{root}sw.js` only when `location.protocol` is http/https.
- Caching: precache app shell on install; stale-while-revalidate for same-origin GETs; man pages cached after first visit.

- [ ] **Step 1: Write `build/make_icons.py`** (pure-stdlib PNG writer, reuses the favicon pixel function):

```python
#!/usr/bin/env python3
"""Generate PWA icons (icon-192.png, icon-512.png) from the favicon pixel art."""
import struct
import sys
import zlib

import make_favicon as fav


def chunk(tag, data):
    c = struct.pack('>I', len(data)) + tag + data
    return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)


def write_png(path, size):
    rows = b''
    for y in range(size):
        row = b'\x00'
        for x in range(size):
            b, g, r, a = fav.pixel(x * fav.SIZE // size, y * fav.SIZE // size)
            row += bytes((r, g, b, a))
        rows += row
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
           + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)
    print('wrote %s (%d bytes)' % (path, len(png)))


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'docs/assets'
    write_png(out + '/icon-192.png', 192)
    write_png(out + '/icon-512.png', 512)
```

Run from `build/`: `cd build && python3 make_icons.py ../docs/assets`. Verify both PNGs open in the browser.

- [ ] **Step 2: Write `docs/manifest.webmanifest`:**

```json
{
  "name": "manpages — offline linux manual",
  "short_name": "manpages",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "background_color": "#090c0d",
  "theme_color": "#090c0d",
  "description": "Offline Linux man page lookup. Zero network calls.",
  "icons": [
    { "src": "assets/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "assets/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- [ ] **Step 3: Write `build/templates/sw.js`:**

```js
/* Service worker: precache the shell, stale-while-revalidate everything else.
   Version is stamped by build_site.py; a new corpus build invalidates all caches. */
var VERSION = '{version}';
var CACHE = 'manpages-' + VERSION;
var SHELL = [
  './', 'index.html', '404.html', 'about.html',
  'manifest.webmanifest', 'favicon.svg', 'favicon.ico',
  'assets/tokens.css', 'assets/app.css', 'assets/pet.css',
  'assets/app.js', 'assets/search-core.js', 'assets/pet.js',
  'assets/icon-192.png', 'assets/icon-512.png',
  'assets/fonts/JetBrainsMono-Regular.woff2', 'assets/fonts/JetBrainsMono-Bold.woff2',
  'assets/fonts/JetBrainsMono-Italic.woff2', 'assets/fonts/JetBrainsMono-BoldItalic.woff2',
  'data/index.js'
];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(SHELL); })
    .then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') return;
  var url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(function (c) {
    return c.match(e.request).then(function (hit) {
      var refresh = fetch(e.request).then(function (res) {
        if (res && res.ok) c.put(e.request, res.clone());
        return res;
      }).catch(function () { return hit; });
      return hit || refresh;
    });
  }));
});
```

- [ ] **Step 4: build_site.py** — after writing `data/index.js`, add:

```python
    import hashlib as _hl
    with open(os.path.join(out, 'data', 'index.js'), 'rb') as f:
        idx_hash = _hl.md5(f.read()).hexdigest()[:8]
    sw_tpl_path = os.path.join(args.templates, 'sw.js')
    if os.path.exists(sw_tpl_path):
        with open(sw_tpl_path, encoding='utf-8') as f:
            sw = f.read().replace('{version}', '%s-%s' % (gen_date, idx_hash))
        with open(os.path.join(out, 'sw.js'), 'w', encoding='utf-8') as f:
            f.write(sw)
```

Also: `run_all.sh`/resume copy step must copy `sw.js` alongside `man/` and `data/` (change the `cp` line to `cp -r "$OUT/man" "$OUT/data" "$DOCS/" && cp "$OUT/sw.js" "$DOCS/" 2>/dev/null || true`).

- [ ] **Step 5: Registration** — template + index.html, last thing before `</body>`:

```html
<script>if('serviceWorker' in navigator && /^https?:$/.test(location.protocol)){navigator.serviceWorker.register('{root}sw.js');}</script>
```

(index.html uses `sw.js` instead of `{root}sw.js`.) Add `<link rel="manifest" href="{root}manifest.webmanifest">` / `href="manifest.webmanifest"` in both heads.

- [ ] **Step 6: Verify in preview** — after a build (Task 12 for the full site; for now run build_site against the existing workdir to get docs/sw.js): reload home, then eval `navigator.serviceWorker.ready.then(r=>r.active.state)` → `activated`; `caches.keys()` → one `manpages-…` cache; open a man page, re-eval cache match for that page → present. Confirm `file://` guard by code review (protocol test).

- [ ] **Step 7: Commit** `feat: installable PWA with offline caching`

---

### Task 10: Package provenance (pipeline)

**Files:**
- Modify: `build/unpack.sh`, `build/extract.sh`, `build/build_site.py`, `build/templates/page.html`
- Test: `build/test_build_site.py`

**Interfaces:**
- `unpack.sh` additionally writes `<workdir>/filemap.tsv`: `manN/<basename><TAB>pkg<TAB>version` (from each deb's extracted file list; deb filename `name_ver_arch.deb`, `%3a` decoded to `:`).
- `extract.sh` writes a 4th `pages.tsv` column: `manDIR/<basename>` (key into filemap). Sample runs (no debs) still produce 4 columns.
- `build_site.py` loads filemap when present and renders `{source}` in the page footer: `source: <pkg> <version>` or empty. Template gains `{source}`.

- [ ] **Step 1: TDD** — add to `test_build_site.py`:

```python
    def test_load_pages_tolerates_three_or_four_cols(self):
        rows = build_site.parse_page_rows(['a\t1\t1/a.1', 'b\t1\t1/b.1\tman1/b.1.gz'])
        self.assertEqual(rows[0], ('a', '1', '1/a.1', ''))
        self.assertEqual(rows[1], ('b', '1', '1/b.1', 'man1/b.1.gz'))
```

Implement `parse_page_rows(lines)` in build_site (split maxsplit 3, pad to 4) and refactor the existing pages.tsv loading to use it. Run test → pass.

- [ ] **Step 2: `unpack.sh`** — replace `one()`:

```bash
MANIF=$WORK/manifests
rm -rf "$MANIF"; mkdir -p "$MANIF"
export MANIF

one() {
  local deb=$1 base pkg ver
  base=${deb##*/}; base=${base%.deb}
  pkg=${base%%_*}
  ver=${base#*_}; ver=${ver%_*}; ver=${ver//%3a/:}
  dpkg-deb --fsys-tarfile "$deb" 2>/dev/null \
    | tar -xv -C "$DEST" --wildcards './usr/share/man/man[1-9]*' 2>/dev/null \
    | awk -v p="$pkg" -v v="$ver" -F/ '/[^/]$/ { print $(NF-1) "/" $NF "\t" p "\t" v }' \
    > "$MANIF/$base.tsv" || true
}
```

and after the xargs run: `cat "$MANIF"/*.tsv > "$WORK/filemap.tsv" 2>/dev/null || : > "$WORK/filemap.tsv"` then `echo "==> filemap: $(wc -l < "$WORK/filemap.tsv") entries"`.

- [ ] **Step 3: `extract.sh`** — the canonical-page emit line becomes:

```bash
    printf '%s\t%s\t%s\t%s\n' "$name" "$sect" "$sect/$stem" "${dir##*/}/$base" >> "$WORK/pages.tsv"
```

(`desc_one` uses `cut -f3` already — unchanged.) `convert.sh` uses `cut -f3` — unchanged.

- [ ] **Step 4: `build_site.py`** — load `filemap.tsv` into `{key: (pkg, ver)}`; page dict gains `src_key`; footer substitution:

```python
    fm = dict((r[0], (r[1], r[2])) for r in load_tsv(os.path.join(work, 'filemap.tsv'), 3))
    ...
    pkg = fm.get(p.get('src_key', ''))
    source_html = ('source: %s %s · ' % (html.escape(pkg[0]), html.escape(pkg[1]))) if pkg else ''
    page_html = ... .replace('{source}', source_html) ...
```

Template footer becomes: `<footer class="page-foot">{source}ubuntu 24.04 lts (noble) · generated {generated} · fully offline</footer>`

- [ ] **Step 5: Re-run unit tests; run the limited pipeline (`PKG_LIMIT=200 run_all.sh` into a scratch workdir) and confirm a page footer shows `source: tar 1.35+...`.**

- [ ] **Step 6: Commit** `feat: package provenance in page footers`

---

### Task 11: Browse pages + About page

**Files:**
- Modify: `build/build_site.py`, `build/templates/page.html` (header nav links), `docs/index.html` (footer links)
- Create: `build/templates/listing.html`
- Test: `build/test_build_site.py`

**Interfaces:**
- Generated: `docs/browse/index.html` (sections with counts), `docs/browse/<sect>.html` or `docs/browse/<sect>-<n>.html` chunks of ≤2000 entries (chunk labels "a–c" style), `docs/about.html` (counts, snapshot date, suites/components, licenses).
- `chunk_entries(entries, limit=2000) -> [(label, [entries])]` is unit-tested. Browse pages live one directory deep → `{root}` = `../`.

- [ ] **Step 1: TDD** — add:

```python
    def test_chunk_entries(self):
        entries = [('a%d' % i,) for i in range(3)] + [('b0',), ('c0',)]
        chunks = build_site.chunk_entries(entries, limit=3)
        self.assertEqual([c[0] for c in chunks], ['a', 'b–c'])
        self.assertEqual(sum(len(c[1]) for c in chunks), 5)
        one = build_site.chunk_entries(entries, limit=100)
        self.assertEqual(len(one), 1)
```

Implement: group sorted entries by lowercased first character; greedily pack whole letter-groups into chunks of ≤limit (a single letter-group larger than limit becomes its own chunk); label = first letter or `first–last`. Run → pass.

- [ ] **Step 2: `build/templates/listing.html`** — the page.html shell with `{content}` replacing the toc+article block:

```html
<!DOCTYPE html>
<html lang="en" data-root="{root}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#090c0d" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f5f7f4" media="(prefers-color-scheme: light)">
<title>{title} — manpages</title>
<link rel="icon" href="{root}favicon.svg" type="image/svg+xml">
<link rel="icon" href="{root}favicon.ico" sizes="32x32">
<link rel="manifest" href="{root}manifest.webmanifest">
<link rel="stylesheet" href="{root}assets/tokens.css">
<link rel="stylesheet" href="{root}assets/app.css">
<link rel="stylesheet" href="{root}assets/pet.css">
<script>try{var t=localStorage.getItem('twb-theme');if(t)document.documentElement.setAttribute('data-theme',t);var pm=localStorage.getItem('twb-pet');if(pm!=='cursor')document.documentElement.setAttribute('data-pet',pm==='off'?'off':'float');var ps=parseInt(localStorage.getItem('twb-pet-size'),10);if(ps>=16&&ps<=64)document.documentElement.style.setProperty('--pet-size',ps+'px');var po=parseInt(localStorage.getItem('twb-pet-opacity'),10);if(po>=15&&po<=100)document.documentElement.style.setProperty('--pet-base-opacity',(po/100).toFixed(3));}catch(e){}</script>
</head>
<body>
<header class="site-header">
  <a class="brand" href="{root}index.html">man<span class="brand-accent">pages</span></a>
  <div class="search-wrap">
    <span class="prompt-char">❯</span>
    <input id="search" type="search" role="combobox" aria-expanded="false" aria-controls="results" aria-autocomplete="list" aria-label="Search man pages" placeholder="search man pages  ( / )" autocomplete="off" spellcheck="false">
    <ul id="results" role="listbox" aria-label="Search results" hidden></ul>
  </div>
  <a class="nav-link" href="{root}browse/index.html">browse</a>
  <button id="theme-toggle" type="button" title="toggle theme">◐</button>
  <button id="pet-open" type="button" title="pet settings" aria-haspopup="true" aria-expanded="false"><svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><path class="pet-body" d="M2 16 V7 Q2 1 8 1 Q14 1 14 7 V16 L12 14.4 L10 16 L8 14.4 L6 16 L4 14.4 Z"/><g class="pet-eyes-open"><rect x="5" y="6" width="2" height="3"/><rect x="9" y="6" width="2" height="3"/></g></svg></button>
</header>
<div id="pet-panel" hidden>
  <div class="settings-head"><span>Pet</span><button id="pet-close" class="menu-close" type="button" aria-label="Close pet panel">&times;</button></div>
  <div class="pet-group-label">Appearance</div>
  <div id="pet-mode" class="pet-seg" role="group" aria-label="Pet mode"><button data-mode="float">Roam</button><button data-mode="cursor">Cursor</button><button data-mode="off">Off</button></div>
  <label class="pet-slider"><span>Size</span><input id="pet-size" type="range" min="16" max="64" step="2"></label>
  <label class="pet-slider"><span>Opacity</span><input id="pet-opacity" type="range" min="15" max="100" step="5"></label>
  <div id="pet-color" class="pet-swatches" role="group" aria-label="Pet color"><button data-color="0" style="--sw:var(--twb-accent)"></button><button data-color="1" style="--sw:var(--twb-accent-alt)"></button><button data-color="2" style="--sw:var(--twb-warm)"></button><button data-color="3" style="--sw:var(--twb-violet)"></button><button data-color="4" style="--sw:var(--twb-orange)"></button><button data-color="5" style="--sw:var(--twb-red)"></button></div>
  <div class="pet-group-label">Behavior</div>
  <button id="pet-q-nap" class="settings-row pet-quirk" type="button"><span class="settings-label">Nap when idle</span><span class="settings-val"></span></button>
  <button id="pet-q-flee" class="settings-row pet-quirk" type="button"><span class="settings-label">Flee from cursor</span><span class="settings-val"></span></button>
  <button id="pet-q-read" class="settings-row pet-quirk" type="button"><span class="settings-label">Read along</span><span class="settings-val"></span></button>
  <button id="pet-q-tricks" class="settings-row pet-quirk" type="button"><span class="settings-label">Do tricks</span><span class="settings-val"></span></button>
  <button id="pet-q-speech" class="settings-row pet-quirk" type="button"><span class="settings-label">Speech bubbles</span><span class="settings-val"></span></button>
</div>
<main class="page listing">
  <article class="man-content" id="content">
{content}
  </article>
</main>
<div id="site-pet" aria-hidden="true"><div class="pet-tilt"><div class="pet-sprite" title="pet the ghost to recolor it"><svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><path class="pet-body" d="M2 16 V7 Q2 1 8 1 Q14 1 14 7 V16 L12 14.4 L10 16 L8 14.4 L6 16 L4 14.4 Z"/><g class="pet-eyes-open"><rect x="5" y="6" width="2" height="3"/><rect x="9" y="6" width="2" height="3"/></g><g class="pet-eyes-closed"><rect x="5" y="8" width="2" height="1"/><rect x="9" y="8" width="2" height="1"/></g><g class="pet-eyes-happy"><path d="M4.6 8 L6 6.6 L7.4 8"/><path d="M8.6 8 L10 6.6 L11.4 8"/></g></svg></div></div></div>
<script src="{root}data/index.js" defer></script>
<script src="{root}assets/search-core.js" defer></script>
<script src="{root}assets/app.js" defer></script>
<script src="{root}assets/pet.js" defer></script>
<script>if('serviceWorker' in navigator && /^https?:$/.test(location.protocol)){navigator.serviceWorker.register('{root}sw.js');}</script>
</body>
</html>
```

- [ ] **Step 3: `build_site.py` generation** (after index.js writing):

```python
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

def write_listings(pages, out, tpl, gen_date):
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
                        .replace('{title}', 'section %s%s' % (sect, '' if len(chunks) == 1 else ' ' + label))
                        .replace('{content}', '\n'.join(body)))
            files.append((fname, label))
        sect_links.append((sect, len(entries), files))
    idx = ['<h1 class="Sh">browse by section</h1><ul class="listing-list">']
    for sect, count, files in sect_links:
        links = ' '.join('<a href="%s">%s</a>' % (html.escape(f), html.escape(l))
                         for f, l in files) if len(files) > 1 else \
                '<a href="%s">all</a>' % html.escape(files[0][0])
        idx.append('<li><b>man%s</b> — %s <span class="l-desc">%d pages</span> · %s</li>'
                   % (html.escape(sect), html.escape(SECTION_NAMES.get(sect[0], '')), count, links))
    idx.append('</ul>')
    with open(os.path.join(browse_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(tpl.replace('{root}', '../').replace('{title}', 'browse')
                .replace('{content}', '\n'.join(idx)))

def write_about(pages, aliases, out, tpl, gen_date):
    body = '''<h1 class="Sh">about</h1>
<p>Offline Linux manual: %d man pages (%d aliases) pre-rendered from
Ubuntu 24.04 LTS (noble + noble-updates, main + universe, amd64), snapshot %s.</p>
<p>Everything is static and self-contained: no CDNs, no external fonts, no
analytics, no network calls. Works from GitHub/GitLab Pages, any web server,
or straight off disk.</p>
<h1 class="Sh">licenses</h1>
<p>Site tooling: MIT. Man page content: upstream Ubuntu package licenses
(see each page footer for its source package). Theme:
terminal-workbench-design-system (MIT). Font: JetBrains Mono (OFL 1.1).</p>''' % (
        len(pages), aliases, gen_date)
    with open(os.path.join(out, 'about.html'), 'w', encoding='utf-8') as f:
        f.write(tpl.replace('{root}', './').replace('{title}', 'about')
                .replace('{content}', body))
```

Call both from `main()` with the listing template; `link-check`: add generated browse hrefs into the existing validation (`../man/...` links from browse pages point at `p['path']` which is guaranteed written — assert by construction, and the audit script covers it post-build). Note about.html mentions main+universe — matches Task 12.

- [ ] **Step 4: Wire links** — page.html header gets the same `<a class="nav-link" href="{root}browse/index.html">browse</a>`; index.html hints line gains ` · <a href="browse/index.html">browse</a> · <a href="about.html">about</a>`. `app.css`:

```css
.nav-link { color: var(--twb-text-muted); font-size: 13px; white-space: nowrap; }
.nav-link:hover { color: var(--twb-accent); text-decoration: none; }
.listing .listing-list { list-style: none; padding: 0; columns: 2; column-gap: 40px; }
.listing .listing-list li { padding: 2px 0; break-inside: avoid; }
.listing .l-desc { color: var(--twb-text-muted); font-size: 12px; }
@media (max-width: 760px) { .listing .listing-list { columns: 1; } }
```

Note: `search-wrap`'s `max-width: 560px` keeps the header from crowding; verify browse link fits at 760px.

- [ ] **Step 5: Run unit tests; regenerate from the existing workdir; browser-verify browse index → section page → man page chain and about.html.**

- [ ] **Step 6: Commit** `feat: browse-by-section and about pages`

---

### Task 12: Universe corpus + the one full rebuild

**Files:**
- Modify: `build/fetch.sh` (components), `build/run_all.sh` (sw.js copy — done in Task 9), `docs/` (regenerated wholesale)

**Interfaces:**
- `COMPONENTS` env (default `main universe`); Contents filter accepts `sect/pkg` (main) and `universe/sect/pkg`; Packages fetched per suite × component; download list gains a size column and prints total GB.

- [ ] **Step 1: fetch.sh changes.** Component env + Packages loop:

```bash
COMPONENTS=${COMPONENTS:-main universe}
...
for s in $SUITES; do
  curl -fsSL --retry 3 -o "$CACHE/indexes/Contents-$s.gz" "$MIRROR/dists/$s/Contents-amd64.gz"
  for c in $COMPONENTS; do
    curl -fsSL --retry 3 -o "$CACHE/indexes/Packages-$s-$c.gz" "$MIRROR/dists/$s/$c/binary-amd64/Packages.gz"
  done
done
```

Contents awk (COMPONENTS-aware):

```bash
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
```

Packages zcat loop becomes `for s in $SUITES; do for c in $COMPONENTS; do zcat "$CACHE/indexes/Packages-$s-$c.gz"; done; done` and the stanza awk also captures `Size:` (substr($i,7)) as a 4th column. After `join`, print the plan:

```bash
awk -F'\t' '{ s += $4 } END { printf "    total download: %.1f GB\n", s / 1e9 }' "$CACHE/download.tsv"
```

`dl()` reads 3 fields now — change `cut -f2,3` to `cut -f2,3` (unchanged; size column is 4th, not passed).

- [ ] **Step 2: Preflight** — run fetch with `PKG_LIMIT=1` just to build indexes/lists; record package count (expect ~12–20k) and total GB (expect ~15–30 GB). Check WSL free space ≥ 2× that (`df -h /home`). If below, stop and report to the user.

- [ ] **Step 3: Full pipeline, background, WSL-native work dir** (same runbook as the v1.0 build; script file, `JOBS=12`). Duration: several hours (download dominates). Monitor via output file + Monitor tool. Deb cache from v1.0 is reused (main debs already present).

- [ ] **Step 4: Validate:** build_site exits 0; `pre` fallback ≤2%; site-report reviewed; expected page count roughly 45–65k. `git add docs` size check: `git count-objects -vH` after commit must stay under ~700 MB pack; if it exceeds 1 GB, stop and surface options (e.g., drop universe section-3 perl/lib pages) rather than pushing.
- [ ] **Step 5: Full test suite + `audit_links.py --sample 5000` + browser spot-checks (`tmux`, `jq`, `htop`, `nmap` now resolve; provenance footers show universe packages).**
- [ ] **Step 5b: Commit the corpus manifest for auditability:** copy `$WORK/filemap.tsv` to `build/corpus-manifest.tsv` (page file → source package + exact version, ~2 MB) and include it in the corpus commit. A rebuild can be diffed against it.
- [ ] **Step 6: Commit** `feat: universe component — full corpus (~Nk pages)` **and push.**

---

### Task 13: README screenshots + copy refresh

**Files:**
- Create: `.github/screenshots/home.png`, `.github/screenshots/page.png`
- Modify: `README.md`

- [ ] **Step 1: Capture with Edge headless (Windows side, live site):**

```powershell
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
& $edge --headless=new --disable-gpu --window-size=1280,800 --screenshot="C:\Users\Matt\Documents\manpages\.github\screenshots\home.png" "https://real-fruit-snacks.github.io/manpages/"
& $edge --headless=new --disable-gpu --window-size=1280,800 --screenshot="C:\Users\Matt\Documents\manpages\.github\screenshots\page.png" "https://real-fruit-snacks.github.io/manpages/man/1/tar.html"
```

(Fallback if Edge headless misbehaves: browser-pane screenshot tool, saved via a scratch HTML download; last resort: skip images, note it.) View both PNGs with Read to confirm they rendered (dark theme, content visible).

- [ ] **Step 2: README update** — embed screenshots at top; refresh feature list (universe corpus + page count, browse/about, PWA install, print, provenance, recently viewed, section-filter syntax `tar 5`, a11y); document CI badge (`![ci](https://github.com/Real-Fruit-Snacks/manpages/actions/workflows/ci.yml/badge.svg)`) and tag-driven releases.

- [ ] **Step 3: Commit** `docs: screenshots and feature overview`

---

### Task 14: Ship v1.2.0 and verify

- [ ] **Step 1:** CHANGELOG: rename `## [Unreleased]` to `## [1.2.0] - <today>` listing every Task 1–13 change; add fresh `## [Unreleased]` above. Commit `chore: changelog for 1.2.0`.
- [ ] **Step 2:** Push `main`; confirm CI workflow goes green on GitHub (`gh run watch`).
- [ ] **Step 3:** `git tag v1.2.0 && git push origin v1.2.0`; confirm the release workflow produces the release with zip + changelog notes (`gh release view v1.2.0`).
- [ ] **Step 4:** Live verification: Pages serves new corpus (curl `tmux.html` 200, provenance footer present, `browse/index.html` 200, `about.html` 200, `sw.js` 200, `manifest.webmanifest` 200); browser pass (combobox a11y tree, service worker activated, recently-viewed, print PDF, section-filter search, ghost still roaming); zero external-origin requests.
- [ ] **Step 5:** Report: page count, repo size, download stats, anything deferred.

---

## Execution notes

- Tasks 1–3 are independent of 4–11; 4 must precede 5; 9's sw.js SHELL includes `about.html` so 11 must land before the Task 12 build (it does). Task 12 is the only multi-hour step.
- Between Tasks 5–11, keep verifying against the *existing* 20k-page docs; only Task 12 regenerates.
- Every task ends in its own commit; nothing is pushed until Task 12's corpus commit (then normal pushes).
