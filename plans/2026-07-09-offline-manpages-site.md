# Offline Man-Page Lookup Site — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> Note: plans live in `plans/` (not the skill-default `docs/superpowers/plans/`) because
> `docs/` is reserved as the GitHub Pages publish root. Spec: `specs/2026-07-09-offline-manpages-site-design.md`.

**Goal:** A fully self-contained GitHub Pages site (published from `docs/`) that serves ~15–20k pre-rendered Ubuntu man pages with instant client-side name/description search, zero network calls, deployable to an air-gapped GitHub Enterprise instance.

**Architecture:** A build pipeline (bash + python, run inside WSL Ubuntu 22.04) fetches Ubuntu `noble` main-component debs, extracts English man pages, converts them to HTML fragments with mandoc (groff → `<pre>` fallbacks), wraps them in an app-shell template, and emits a compact search index as a JS file. Everything generated is committed. The client is ~200 lines of dependency-free JS.

**Tech Stack:** bash, python3 (stdlib only), mandoc, groff, lexgrog, node (tests only), vanilla JS/CSS, terminal-workbench-design-system tokens (vendored), JetBrains Mono (vendored).

## Global Constraints

- The published site (`docs/`) makes **zero network requests**: no CDN, no external fonts, no fetch of external origins. All assets are committed files referenced by **relative paths only**.
- The site must work when opened via `file://` — therefore the search index is a `.js` file (`window.MANDB = {...}`), never fetched JSON.
- Corpus: Ubuntu 24.04 LTS (`noble` + `noble-updates`), `main` component, amd64, English pages, man sections 1–9.
- Build aborts if more than **2%** of pages land in the `<pre>` fallback.
- Filenames emitted under `docs/` must be NTFS-safe (no `: < > " \ | ? *`, no case-insensitive collisions) — the repo is cloned on Windows.
- All shell/py sources use **LF** line endings (enforced via `.gitattributes`); scripts run in WSL.
- Windows-side repo path: `C:\Users\Matt\Documents\manpages` = WSL `/mnt/c/Users/Matt/Documents/manpages` (call it `$REPO`).
- Heavy build I/O happens in WSL-native `$HOME/manbuild` (9p `/mnt/c` is too slow for 40k small files); only final output is copied to `$REPO/docs`.
- Run WSL commands from Windows as: `wsl.exe -d Ubuntu-22.04 -- bash -c '<cmd>'`.
- Dark theme is default; light mode via `prefers-color-scheme` and a `data-theme` override persisted to `localStorage` key `twb-theme`.

---

### Task 1: Repo hygiene + vendored assets

**Files:**
- Create: `.gitattributes`, `.gitignore`, `.claude/launch.json`
- Create: `docs/assets/tokens.css` (vendored), `docs/assets/fonts/*.woff2` + `docs/assets/fonts/OFL.txt` (vendored)

**Interfaces:**
- Produces: `docs/assets/tokens.css` defining `--twb-bg-0..4, --twb-text-normal/-muted/-faint/-soft, --twb-accent, --twb-accent-alt, --twb-warm, --twb-orange, --twb-red, --twb-violet, --twb-border, --twb-border-strong, --twb-font-mono, --twb-font-ui, --twb-radius-s/m/l/pill, --twb-selection, --twb-focus-ring, --twb-tag-bg, --twb-tag-border, --twb-transition, --twb-line-height*` — consumed by `app.css` (Task 3). Dark default; light via `@media (prefers-color-scheme: light)` and `[data-theme]` overrides.
- Produces: font files `JetBrainsMono-{Regular,Bold,Italic,BoldItalic}.woff2` consumed by `@font-face` in `app.css`.

- [ ] **Step 1: Write `.gitattributes`** (LF for everything that runs in WSL)

```
* text=auto
*.sh text eol=lf
*.py text eol=lf
*.js text eol=lf
*.css text eol=lf
*.html text eol=lf
*.md text eol=lf
*.woff2 binary
```

- [ ] **Step 2: Write `.gitignore`**

```
build/cache/
build/work/
__pycache__/
*.pyc
```

- [ ] **Step 3: Write `.claude/launch.json`** (static preview server, serves `docs/` from WSL)

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "manpages",
      "runtimeExecutable": "wsl.exe",
      "runtimeArgs": ["-d", "Ubuntu-22.04", "--", "python3", "-m", "http.server", "8321", "--directory", "/mnt/c/Users/Matt/Documents/manpages/docs"],
      "port": 8321
    }
  ]
}
```

- [ ] **Step 4: Vendor tokens.css and fonts** (run from Windows Bash tool; `curl` + `unzip` in WSL)

```
wsl.exe -d Ubuntu-22.04 -- bash -c '
set -e
REPO=/mnt/c/Users/Matt/Documents/manpages
mkdir -p "$REPO/docs/assets/fonts"
curl -fsSL https://raw.githubusercontent.com/Real-Fruit-Snacks/terminal-workbench-design-system/main/tokens.css -o "$REPO/docs/assets/tokens.css"
cd /tmp && curl -fsSL -o jbm.zip https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip
rm -rf jbm && mkdir jbm && cd jbm && unzip -q ../jbm.zip
for w in Regular Bold Italic BoldItalic; do cp fonts/webfonts/JetBrainsMono-$w.woff2 "$REPO/docs/assets/fonts/"; done
cp OFL.txt "$REPO/docs/assets/fonts/"
ls -la "$REPO/docs/assets/fonts/"'
```

Expected: tokens.css ~5.7 KB; 4 woff2 files (~90–110 KB each) + OFL.txt listed. If `unzip` is missing, `apt-get install -y unzip` as root first (`wsl.exe -d Ubuntu-22.04 -u root -- apt-get install -y unzip`). If the zip layout differs, locate the woff2 files with `find jbm -name '*.woff2'` and copy the four weights from wherever they are.

- [ ] **Step 5: Verify tokens.css contains expected variables**

Run: `grep -c 'twb-accent\|twb-bg-0\|data-theme' docs/assets/tokens.css` (Grep tool is fine too)
Expected: count ≥ 3.

- [ ] **Step 6: Commit**

```
git add .gitattributes .gitignore .claude/launch.json docs/assets
git commit -m "chore: scaffold repo, vendor design tokens and fonts"
```

---

### Task 2: Search core (pure logic, node-tested)

**Files:**
- Create: `docs/assets/search-core.js`
- Test: `build/test_search.js`

**Interfaces:**
- Produces: `SearchCore.search(db, query, limit)` → array of `{name, section, desc, path, score, alias?}`, sorted best-first, deduped by `path`, `limit` default 50. Exposed as `window.SearchCore` in browsers and `module.exports` under node. Consumed by `app.js` (Task 3).
- Consumes: `db` in the MANDB format: `{v:1, pages:[[name, section, desc, path], ...], aliases:[[name, section, pageIndex], ...]}` (produced later by `build_site.py`; tests use a fixture).

- [ ] **Step 1: Write the failing test — `build/test_search.js`**

```js
'use strict';
var assert = require('assert');
var SearchCore = require('../docs/assets/search-core.js');

var db = { v: 1, pages: [
  ['tar', '1', 'an archiving utility', 'man/1/tar.html'],
  ['target', '1', 'systemd target units', 'man/1/target.html'],
  ['star', '1', 'unique standard tape archiver', 'man/1/star.html'],
  ['grep', '1', 'print lines matching a pattern', 'man/1/grep.html'],
  ['fstab', '5', 'static file system information', 'man/5/fstab.html']
], aliases: [ ['untar', '1', 0], ['egrep', '1', 3] ] };

var r = SearchCore.search(db, 'tar', 10);
assert.strictEqual(r[0].name, 'tar', 'exact match first');
assert.strictEqual(r[1].name, 'target', 'prefix beats substring');
assert.ok(r.some(function (x) { return x.name === 'star'; }), 'substring included');
r.forEach(function (x, i) { r.forEach(function (y, j) {
  if (i < j) assert.notStrictEqual(x.path, y.path, 'deduped by path'); }); });

r = SearchCore.search(db, 'archiving', 10);
assert.strictEqual(r[0].name, 'tar', 'description match');

r = SearchCore.search(db, 'untar', 10);
assert.strictEqual(r[0].path, 'man/1/tar.html', 'alias resolves to target page');

r = SearchCore.search(db, 'file system', 10);
assert.strictEqual(r[0].name, 'fstab', 'multi-token AND across desc');

assert.strictEqual(SearchCore.search(db, '', 10).length, 0, 'empty query');
assert.strictEqual(SearchCore.search(db, '   ', 10).length, 0, 'blank query');
assert.strictEqual(SearchCore.search(db, 'tar', 2).length, 2, 'limit respected');
assert.strictEqual(SearchCore.search(db, 'zzzz', 10).length, 0, 'no matches');

console.log('search-core: all tests passed');
```

- [ ] **Step 2: Run test to verify it fails**

Run: `wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages && node build/test_search.js'`
Expected: FAIL — `Cannot find module '../docs/assets/search-core.js'`

- [ ] **Step 3: Write `docs/assets/search-core.js`**

```js
/* SearchCore — pure man-page index matching. UMD so node tests can load it. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) { module.exports = factory(); }
  else { root.SearchCore = factory(); }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  function scoreName(name, tok) {
    if (name === tok) return 100;
    if (name.indexOf(tok) === 0) return 80;
    if (name.indexOf(tok) !== -1) return 60;
    return 0;
  }

  function search(db, query, limit) {
    limit = limit || 50;
    var q = String(query || '').trim().toLowerCase();
    if (!q || !db || !db.pages) return [];
    var tokens = q.split(/\s+/);
    var results = [];
    var pages = db.pages;
    var i, t, s;

    for (i = 0; i < pages.length; i++) {
      var name = pages[i][0].toLowerCase();
      var desc = (pages[i][2] || '').toLowerCase();
      var total = 0, ok = true;
      for (t = 0; t < tokens.length; t++) {
        s = scoreName(name, tokens[t]);
        if (!s && desc.indexOf(tokens[t]) !== -1) s = 30;
        if (!s) { ok = false; break; }
        total += s;
      }
      if (ok) results.push({ name: pages[i][0], section: pages[i][1],
        desc: pages[i][2] || '', path: pages[i][3], score: total });
    }

    var aliases = db.aliases || [];
    for (i = 0; i < aliases.length; i++) {
      var an = aliases[i][0].toLowerCase();
      var total2 = 0, ok2 = true;
      for (t = 0; t < tokens.length; t++) {
        s = scoreName(an, tokens[t]);
        if (!s) { ok2 = false; break; }
        total2 += s - 10; /* alias slightly below a real page hit */
      }
      if (ok2) {
        var p = pages[aliases[i][2]];
        if (p) results.push({ name: aliases[i][0], section: aliases[i][1],
          desc: 'alias for ' + p[0] + '(' + p[1] + ')' + (p[2] ? ' — ' + p[2] : ''),
          path: p[3], score: total2, alias: true });
      }
    }

    results.sort(function (x, y) {
      if (y.score !== x.score) return y.score - x.score;
      if (x.name.length !== y.name.length) return x.name.length - y.name.length;
      if (x.name !== y.name) return x.name < y.name ? -1 : 1;
      return x.section < y.section ? -1 : 1;
    });

    var seen = {}, out = [];
    for (i = 0; i < results.length && out.length < limit; i++) {
      if (!seen[results[i].path]) { seen[results[i].path] = 1; out.push(results[i]); }
    }
    return out;
  }

  return { search: search };
}));
```

- [ ] **Step 4: Run test to verify it passes**

Run: `wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages && node build/test_search.js'`
Expected: `search-core: all tests passed`

- [ ] **Step 5: Commit**

```
git add docs/assets/search-core.js build/test_search.js
git commit -m "feat: search core with prefix/substring/alias scoring"
```

---

### Task 3: App shell — home page, 404, styling, UI glue

**Files:**
- Create: `docs/index.html`, `docs/404.html`, `docs/assets/app.css`, `docs/assets/app.js`, `docs/data/index.js` (temporary 5-entry sample, later regenerated)

**Interfaces:**
- Consumes: `SearchCore.search` (Task 2); `--twb-*` variables (Task 1); `window.MANDB` global from `data/index.js`.
- Produces: DOM contract used by every generated page (Task 6): elements `#search` (input), `#results` (ul), `#theme-toggle` (button), `<html data-root="...">` attribute giving the relative path to site root. `app.js` reads `data-root` to build result hrefs. Home page additionally has `#page-count`.

- [ ] **Step 1: Write `docs/data/index.js`** (hand-written sample so the shell is testable before the pipeline exists)

```js
window.MANDB={"v":1,"generated":"sample","pages":[["tar","1","an archiving utility","man/1/tar.html"],["grep","1","print lines that match patterns","man/1/grep.html"],["fstab","5","static information about the filesystems","man/5/fstab.html"],["ssh","1","OpenSSH remote login client","man/1/ssh.html"],["systemctl","1","Control the systemd system and service manager","man/1/systemctl.html"]],"aliases":[["untar","1",0],["egrep","1",1]]};
```

- [ ] **Step 2: Write `docs/assets/app.css`**

```css
/* App styles on top of terminal-workbench tokens. All colors come from tokens.css. */

@font-face { font-family: "JetBrains Mono"; src: url("fonts/JetBrainsMono-Regular.woff2") format("woff2"); font-weight: 400; font-style: normal; font-display: swap; }
@font-face { font-family: "JetBrains Mono"; src: url("fonts/JetBrainsMono-Bold.woff2") format("woff2"); font-weight: 700; font-style: normal; font-display: swap; }
@font-face { font-family: "JetBrains Mono"; src: url("fonts/JetBrainsMono-Italic.woff2") format("woff2"); font-weight: 400; font-style: italic; font-display: swap; }
@font-face { font-family: "JetBrains Mono"; src: url("fonts/JetBrainsMono-BoldItalic.woff2") format("woff2"); font-weight: 700; font-style: italic; font-display: swap; }

* { box-sizing: border-box; }
html { height: 100%; }
body {
  margin: 0; min-height: 100%;
  background: var(--twb-bg-0); color: var(--twb-text-normal);
  font-family: "JetBrains Mono", var(--twb-font-mono);
  font-size: 14px; line-height: var(--twb-line-height);
}
a { color: var(--twb-accent-alt); text-decoration: none; }
a:hover { text-decoration: underline; }
::selection { background: var(--twb-selection); }
:focus-visible { outline: 2px solid var(--twb-focus-ring); outline-offset: 1px; }

/* ---- header (man page views) ---- */
.site-header {
  position: sticky; top: 0; z-index: 10;
  display: flex; align-items: center; gap: 16px;
  padding: 8px 16px;
  background: var(--twb-bg-1); border-bottom: var(--twb-border-width) solid var(--twb-border);
}
.brand { color: var(--twb-text-normal); font-weight: 700; white-space: nowrap; }
.brand:hover { text-decoration: none; }
.brand-accent { color: var(--twb-accent); }

/* ---- search ---- */
.search-wrap { position: relative; flex: 1; max-width: 560px; display: flex; align-items: center; }
.prompt-char { color: var(--twb-accent); margin-right: 8px; user-select: none; }
#search {
  flex: 1; padding: 6px 10px;
  background: var(--twb-bg-0); color: var(--twb-text-normal);
  border: var(--twb-border-width) solid var(--twb-border);
  border-radius: var(--twb-radius-s);
  font: inherit; caret-color: var(--twb-accent);
}
#search:focus { border-color: var(--twb-accent); outline: none; }
#search::placeholder { color: var(--twb-text-faint); }
#results {
  position: absolute; top: calc(100% + 4px); left: 0; right: 0;
  margin: 0; padding: 4px; list-style: none;
  max-height: 60vh; overflow-y: auto;
  background: var(--twb-bg-2); border: var(--twb-border-width) solid var(--twb-border-strong);
  border-radius: var(--twb-radius-m); box-shadow: var(--twb-shadow-pane);
}
#results li a {
  display: flex; align-items: baseline; gap: 10px;
  padding: 5px 10px; border-radius: var(--twb-radius-s);
  color: var(--twb-text-normal); text-decoration: none;
}
#results li a:hover, #results li.sel a { background: var(--twb-active-line); }
#results li.sel a { outline: 1px solid var(--twb-accent); }
.r-name { font-weight: 700; white-space: nowrap; }
.r-desc { color: var(--twb-text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.badge {
  font-size: 11px; padding: 0 7px; border-radius: var(--twb-radius-pill);
  background: var(--twb-tag-bg); border: 1px solid var(--twb-tag-border);
  color: var(--twb-text-muted); white-space: nowrap;
}
.badge.s1 { color: var(--twb-accent); }
.badge.s2 { color: var(--twb-accent-alt); }
.badge.s3 { color: var(--twb-violet); }
.badge.s4 { color: var(--twb-orange); }
.badge.s5 { color: var(--twb-warm); }
.badge.s6 { color: var(--twb-accent); }
.badge.s7 { color: var(--twb-accent-alt); }
.badge.s8 { color: var(--twb-red); }
#theme-toggle {
  margin-left: auto; padding: 4px 10px; cursor: pointer;
  background: var(--twb-bg-2); color: var(--twb-text-muted);
  border: var(--twb-border-width) solid var(--twb-border);
  border-radius: var(--twb-radius-s); font: inherit;
}
#theme-toggle:hover { color: var(--twb-text-normal); border-color: var(--twb-border-strong); }

/* ---- home hero ---- */
.home .hero {
  min-height: 80vh; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 14px; padding: 24px;
}
.hero-title { font-size: 42px; margin: 0; font-weight: 700; letter-spacing: -1px; }
.hero-sub { color: var(--twb-text-muted); margin: 0; }
.hero-search { width: 100%; max-width: 640px; }
.hero-search #search { padding: 10px 14px; font-size: 16px; }
.hints { color: var(--twb-text-faint); font-size: 12px; }
.hints kbd {
  background: var(--twb-tag-bg); border: 1px solid var(--twb-tag-border);
  border-radius: var(--twb-radius-s); padding: 1px 6px; font: inherit;
}
.home #theme-toggle { position: fixed; top: 12px; right: 12px; margin: 0; }

/* ---- man page layout ---- */
.page { display: flex; gap: 32px; max-width: 1100px; margin: 0 auto; padding: 24px 16px 64px; }
.toc { width: 210px; flex-shrink: 0; position: sticky; top: 64px; align-self: flex-start;
  max-height: calc(100vh - 90px); overflow-y: auto; }
.toc-title { font-weight: 700; color: var(--twb-accent); margin-bottom: 8px; word-break: break-all; }
.toc ul { list-style: none; margin: 0; padding: 0; border-left: 1px solid var(--twb-border); }
.toc li a { display: block; padding: 3px 10px; color: var(--twb-text-muted); font-size: 12.5px; }
.toc li a:hover { color: var(--twb-text-normal); text-decoration: none; background: var(--twb-active-line); }
.man-content { flex: 1; min-width: 0; }
.page-foot { margin-top: 40px; padding-top: 12px; border-top: 1px solid var(--twb-border);
  color: var(--twb-text-faint); font-size: 12px; }
@media (max-width: 760px) { .page { flex-direction: column; } .toc { position: static; width: auto; max-height: none; } }

/* ---- mandoc output styling ---- */
.man-content table.head, .man-content table.foot { width: 100%; color: var(--twb-text-faint); font-size: 12px; border-collapse: collapse; }
.man-content .head-vol, .man-content .foot-os { text-align: center; }
.man-content .head-rtitle, .man-content .foot-date { text-align: right; }
.man-content h1.Sh, .man-content h1 { font-size: 15px; color: var(--twb-accent); margin: 26px 0 8px; letter-spacing: 0.5px; }
.man-content h2.Ss, .man-content h2 { font-size: 14px; color: var(--twb-text-normal); margin: 20px 0 6px; }
.man-content a.permalink { color: inherit; }
.man-content .Nm, .man-content b, .man-content strong { color: var(--twb-text-normal); font-weight: 700; }
.man-content .Fl, .man-content .Cm, .man-content .Ic { color: var(--twb-warm); font-weight: 700; }
.man-content .Ar, .man-content var, .man-content i, .man-content em { color: var(--twb-accent-alt); font-style: italic; }
.man-content .Pa, .man-content .Ev { color: var(--twb-violet); }
.man-content a.Xr { color: var(--twb-accent); }
.man-content span.Xr { color: var(--twb-text-normal); }
.man-content pre, .man-content .Bd-indent {
  background: var(--twb-bg-1); border: 1px solid var(--twb-border);
  border-radius: var(--twb-radius-m); padding: 10px 14px;
  overflow-x: auto; line-height: var(--twb-line-height-code);
}
.man-content pre.plain-roff { white-space: pre-wrap; }
.man-content dl.Bl-tag > dt { font-weight: 700; margin-top: 10px; }
.man-content dl.Bl-tag > dd { margin-left: 24px; }
.man-content table { border-collapse: collapse; }
.man-content table.tbl td, .man-content table.tbl th { border: 1px solid var(--twb-border); padding: 3px 8px; }
.man-content .manual-text { max-width: 84ch; }
```

- [ ] **Step 3: Write `docs/assets/app.js`**

```js
/* UI glue: theme toggle + search box behavior. Depends on SearchCore and MANDB. */
(function () {
  'use strict';
  var root = document.documentElement.getAttribute('data-root') || './';

  var btn = document.getElementById('theme-toggle');
  if (btn) {
    btn.addEventListener('click', function () {
      var cur = document.documentElement.getAttribute('data-theme');
      if (!cur) {
        cur = (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) ? 'light' : 'dark';
      }
      var next = cur === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('twb-theme', next); } catch (e) { /* private mode */ }
    });
  }

  var input = document.getElementById('search');
  var list = document.getElementById('results');
  if (!input || !list) return;
  var sel = -1, items = [];

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function render() {
    if (!items.length) { list.hidden = true; list.innerHTML = ''; return; }
    var h = '';
    for (var i = 0; i < items.length; i++) {
      var r = items[i];
      h += '<li class="' + (i === sel ? 'sel' : '') + '">' +
        '<a href="' + esc(root + r.path) + '">' +
        '<span class="r-name">' + esc(r.name) + '</span>' +
        '<span class="badge s' + esc(String(r.section).charAt(0)) + '">' + esc(r.section) + '</span>' +
        '<span class="r-desc">' + esc(r.desc) + '</span></a></li>';
    }
    list.innerHTML = h;
    list.hidden = false;
    var s = list.querySelector('li.sel');
    if (s && s.scrollIntoView) s.scrollIntoView({ block: 'nearest' });
  }

  function update() {
    if (!window.MANDB || !window.SearchCore) return;
    items = window.SearchCore.search(window.MANDB, input.value, 30);
    sel = items.length ? 0 : -1;
    render();
  }

  input.addEventListener('input', update);
  input.addEventListener('focus', function () { if (items.length) list.hidden = false; });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { if (sel < items.length - 1) { sel++; render(); } e.preventDefault(); }
    else if (e.key === 'ArrowUp') { if (sel > 0) { sel--; render(); } e.preventDefault(); }
    else if (e.key === 'Enter') { if (sel >= 0 && items[sel]) location.href = root + items[sel].path; }
    else if (e.key === 'Escape') { input.value = ''; items = []; sel = -1; render(); input.blur(); }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== input &&
        !/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) {
      input.focus(); input.select(); e.preventDefault();
    }
  });
  document.addEventListener('click', function (e) {
    if (!list.contains(e.target) && e.target !== input) list.hidden = true;
  });

  var pc = document.getElementById('page-count');
  if (pc && window.MANDB) pc.textContent = window.MANDB.pages.length.toLocaleString();
})();
```

- [ ] **Step 4: Write `docs/index.html`**

```html
<!DOCTYPE html>
<html lang="en" data-root="./">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>manpages — offline linux manual</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ctext y='13' font-size='13'%3E%E2%9D%AF%3C/text%3E%3C/svg%3E">
<link rel="stylesheet" href="assets/tokens.css">
<link rel="stylesheet" href="assets/app.css">
<script>try{var t=localStorage.getItem('twb-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}</script>
</head>
<body class="home">
<button id="theme-toggle" type="button" title="toggle theme">◐</button>
<main class="hero">
  <h1 class="hero-title">man<span class="brand-accent">pages</span></h1>
  <p class="hero-sub">offline linux manual · <span id="page-count">—</span> pages · zero network</p>
  <div class="search-wrap hero-search">
    <span class="prompt-char">❯</span>
    <input id="search" type="search" placeholder="search man pages" autocomplete="off" spellcheck="false" autofocus>
    <ul id="results" hidden></ul>
  </div>
  <p class="hints"><kbd>/</kbd> focus · <kbd>↑</kbd><kbd>↓</kbd> navigate · <kbd>Enter</kbd> open · <kbd>Esc</kbd> clear</p>
</main>
<script src="data/index.js" defer></script>
<script src="assets/search-core.js" defer></script>
<script src="assets/app.js" defer></script>
</body>
</html>
```

- [ ] **Step 5: Write `docs/404.html`** — GitHub Pages serves this at *any* missing path, so it cannot use relative asset links; it is fully self-inlined and computes the site root with JS.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>404 — manpages</title>
<style>
  body { margin:0; min-height:100vh; display:flex; flex-direction:column; align-items:center;
    justify-content:center; gap:12px; background:#090c0d; color:#dce4df;
    font-family:"JetBrains Mono",ui-monospace,Consolas,monospace; }
  @media (prefers-color-scheme: light) { body { background:#f5f7f4; color:#17201d; } }
  a { color:#63f2ab; } .dim { color:#879994; }
</style>
</head>
<body>
<h1>404</h1>
<p class="dim">no manual entry for this path</p>
<p><a id="home" href="./">← back to search</a></p>
<script>
  // Pages serves 404.html at the failing URL's own path; walk back to the site root.
  var p = location.pathname;
  var i = p.indexOf('/man/');
  document.getElementById('home').href = i !== -1 ? p.slice(0, i + 1) : './';
</script>
</body>
</html>
```

- [ ] **Step 6: Verify in the browser.** Use `preview_start` with name `manpages`, then `preview_snapshot` / `preview_click` / `preview_fill`:
  1. Home renders: hero title, page count "5", dark graphite background.
  2. Fill `#search` with `tar` → results list shows `tar(1)` first, then alias `untar`.
  3. `preview_inspect` on `body` → `background-color` is `rgb(9, 12, 13)` (dark) — verify via computed style, not screenshot.
  4. Click `#theme-toggle` → `html[data-theme="light"]` set; body background becomes light (`rgb(245, 247, 244)`).
  5. `preview_console_logs` shows no errors (the result links 404 — expected, no man pages exist yet).
  6. `preview_network` filter `failed`: only `/man/...` navigations may fail; **no external-origin requests at all**.

- [ ] **Step 7: Commit**

```
git add docs
git commit -m "feat: app shell — home, 404, styling, search UI"
```

---

### Task 4: extract.sh — canonical pages, aliases, descriptions

**Files:**
- Create: `build/extract.sh`

**Interfaces:**
- Consumes: a man tree root (`<root>/man1 ... man9*`) — either WSL's own `/usr/share/man` (sample) or the merged deb tree (Task 8).
- Produces, under `<workdir>`:
  - `pages/<sect>/<name>.<sect>` — uncompressed canonical roff sources
  - `pages.tsv` — `name<TAB>sect<TAB>relpath` (relpath = `<sect>/<name>.<sect>`, path under `pages/`)
  - `aliases.tsv` — `alias<TAB>aliassect<TAB>targetname<TAB>targetsect`
  - `descriptions.tsv` — `name<TAB>sect<TAB>one-line description`
  - `extract.log` — skipped/duplicate entries
  Consumed by `convert.sh` (Task 5) and `build_site.py` (Task 6).

- [ ] **Step 1: Write `build/extract.sh`**

```bash
#!/usr/bin/env bash
# extract.sh — collect canonical man pages, aliases (.so + symlinks), and
# one-line descriptions from a man tree.
#
# usage: extract.sh <man-root> <workdir>
#   <man-root>  directory containing man1..man9* (e.g. /usr/share/man)
#   <workdir>   output directory (created); see plan for produced files
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
    printf '%s\t%s\t%s\n' "$name" "$sect" "$sect/$stem" >> "$WORK/pages.tsv"
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
```

- [ ] **Step 2: Run on the sample corpus (WSL's own man pages, WSL-native workdir)**

Run:
```
wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages && bash build/extract.sh /usr/share/man "$HOME/manbuild/sample"'
```
Expected: `==> pages: ~2000–4000, aliases: >100, log: <small>` then `==> descriptions:` ≈ pages count (lexgrog fails on a few — fine). Takes a few minutes (serial zcat loop).

- [ ] **Step 3: Spot-check outputs**

Run:
```
wsl.exe -d Ubuntu-22.04 -- bash -c 'W=$HOME/manbuild/sample; head -3 $W/pages.tsv $W/aliases.tsv $W/descriptions.tsv; grep -P "^tar\t1\t" $W/pages.tsv; grep -P "^tar\t1\t" $W/descriptions.tsv'
```
Expected: sane TSV rows; `tar	1	1/tar.1` present; tar's description `an archiving utility`.

- [ ] **Step 4: Commit**

```
git add build/extract.sh
git commit -m "feat: extract.sh — canonical pages, aliases, lexgrog descriptions"
```

---

### Task 5: convert.sh — roff → HTML fragments with fallback chain

**Files:**
- Create: `build/convert.sh`

**Interfaces:**
- Consumes: `<workdir>/pages.tsv` + `<workdir>/pages/` (Task 4).
- Produces: `<workdir>/html/<relpath>.html` per page (mandoc fragment, or groff full-doc, or `<pre class="plain-roff">`), and `<workdir>/convert-report.tsv` (`relpath<TAB>mandoc|groff|pre`). Consumed by `build_site.py` (Task 6), which strips groff docs to their `<body>` and counts `pre` for the 2% abort rule.

- [ ] **Step 1: Write `build/convert.sh`**

```bash
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
  if ! mandoc -T html -O fragment,man=../%S/%N.html "$src" > "$out" 2>/dev/null || [ ! -s "$out" ]; then
    method=groff
    if ! timeout 30 groff -mandoc -Thtml "$src" > "$out" 2>/dev/null || [ ! -s "$out" ]; then
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
```

- [ ] **Step 2: Run on the sample corpus**

Run:
```
wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages && bash build/convert.sh "$HOME/manbuild/sample"'
```
Expected: `==> converted: N of N`, with method counts dominated by `mandoc` (typically >95%), some `groff`, very few `pre`.

- [ ] **Step 3: Spot-check a fragment**

Run:
```
wsl.exe -d Ubuntu-22.04 -- bash -c 'head -c 600 $HOME/manbuild/sample/html/1/tar.1.html; echo; grep -c "class=\"Xr\"" $HOME/manbuild/sample/html/1/tar.1.html || true'
```
Expected: fragment starting with `<table class="head">`, containing `class="Sh"` headings; Xr count ≥ 0.

- [ ] **Step 4: Commit**

```
git add build/convert.sh
git commit -m "feat: convert.sh — mandoc/groff/pre fallback chain"
```

---

### Task 6: build_site.py — wrap pages, cross-links, index, validation

**Files:**
- Create: `build/build_site.py`, `build/templates/page.html`
- Test: `build/test_build_site.py`

**Interfaces:**
- Consumes: workdir artifacts from Tasks 4–5 (`pages.tsv`, `aliases.tsv`, `descriptions.tsv`, `convert-report.tsv`, `html/`).
- Produces: `<out>/man/<sect>/<slug>.html` (one per page) and `<out>/data/index.js` (`window.MANDB=...` in the format defined in Task 2). Also `<workdir>/site-report.txt`. Exits 1 on validation failure.
- Public functions used by tests: `slugify(name, taken) -> str`, `build_maps(pages) -> (exact, by_base)`, `rewrite_xr(content, exact, by_base, alias_target) -> str`, `extract_toc(content) -> [(id, label)]`.

- [ ] **Step 1: Write the failing tests — `build/test_build_site.py`**

```python
import unittest
import build_site

FRAG = ('<h1 class="Sh" id="NAME"><a class="permalink" href="#NAME">NAME</a></h1>'
        '<p>tar - an archiver</p>'
        '<h1 class="Sh" id="SEE_ALSO"><a class="permalink" href="#SEE_ALSO">SEE ALSO</a></h1>'
        '<p><a class="Xr" href="../1/gzip.html">gzip(1)</a>, '
        '<a class="Xr" href="../1/nope.html">nope(1)</a>, '
        '<a class="Xr" href="../3/foo.html">foo(3ssl)</a></p>')


class TestBuildSite(unittest.TestCase):
    def setUp(self):
        self.pages = [
            {'name': 'gzip', 'sect': '1', 'slug': 'gzip'},
            {'name': 'foo', 'sect': '3ssl', 'slug': 'foo'},
            {'name': 'tar', 'sect': '1', 'slug': 'tar'},
        ]
        self.exact, self.by_base = build_site.build_maps(self.pages)

    def test_slugify_safe_chars(self):
        taken = {}
        self.assertEqual(build_site.slugify('Test::More', taken), 'Test__More')
        self.assertEqual(build_site.slugify('ls', taken), 'ls')

    def test_slugify_case_collision(self):
        taken = {}
        build_site.slugify('ls', taken)
        s = build_site.slugify('LS', taken)  # NTFS is case-insensitive
        self.assertNotEqual(s.lower(), 'ls')

    def test_xr_rewrite_exact_and_miss(self):
        out = build_site.rewrite_xr(FRAG, self.exact, self.by_base, lambda n, s: None)
        self.assertIn('href="../1/gzip.html"', out)
        self.assertIn('<span class="Xr">nope(1)</span>', out)
        self.assertIn('href="../3ssl/foo.html"', out)  # (3ssl) exact section

    def test_xr_base_section_fallback(self):
        frag = '<a class="Xr" href="#">foo(3)</a>'
        out = build_site.rewrite_xr(frag, self.exact, self.by_base, lambda n, s: None)
        self.assertIn('href="../3ssl/foo.html"', out)

    def test_xr_alias_fallback(self):
        frag = '<a class="Xr">bunzip(1)</a>'
        target = self.pages[0]
        out = build_site.rewrite_xr(frag, self.exact, self.by_base,
                                    lambda n, s: target if n == 'bunzip' else None)
        self.assertIn('href="../1/gzip.html"', out)

    def test_extract_toc(self):
        self.assertEqual(build_site.extract_toc(FRAG),
                         [('NAME', 'NAME'), ('SEE_ALSO', 'SEE ALSO')])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages/build && python3 -m unittest test_build_site -v'`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_site'`

- [ ] **Step 3: Write `build/templates/page.html`**

```html
<!DOCTYPE html>
<html lang="en" data-root="{root}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{desc}">
<title>{title} — manpages</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ctext y='13' font-size='13'%3E%E2%9D%AF%3C/text%3E%3C/svg%3E">
<link rel="stylesheet" href="{root}assets/tokens.css">
<link rel="stylesheet" href="{root}assets/app.css">
<script>try{var t=localStorage.getItem('twb-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}</script>
</head>
<body>
<header class="site-header">
  <a class="brand" href="{root}index.html">man<span class="brand-accent">pages</span></a>
  <div class="search-wrap">
    <span class="prompt-char">❯</span>
    <input id="search" type="search" placeholder="search man pages  ( / )" autocomplete="off" spellcheck="false">
    <ul id="results" hidden></ul>
  </div>
  <button id="theme-toggle" type="button" title="toggle theme">◐</button>
</header>
<main class="page">
  <nav class="toc" aria-label="Sections">
    <div class="toc-title">{title}</div>
    <ul>{toc}</ul>
  </nav>
  <article class="man-content">
{content}
  <footer class="page-foot">generated {generated} · ubuntu 24.04 lts (noble) · fully offline</footer>
  </article>
</main>
<script src="{root}data/index.js" defer></script>
<script src="{root}assets/search-core.js" defer></script>
<script src="{root}assets/app.js" defer></script>
</body>
</html>
```

- [ ] **Step 4: Write `build/build_site.py`**

```python
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
```

- [ ] **Step 5: Run unit tests**

Run: `wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages/build && python3 -m unittest test_build_site -v'`
Expected: `OK` — all 6 tests pass.

- [ ] **Step 6: Build the sample site into `docs/`**

Run:
```
wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages && rm -rf docs/man && python3 build/build_site.py --work "$HOME/manbuild/sample" --out docs'
```
Expected: `pages=~2000+ aliases=... pre=...(<2%) ... errors=0`, exit 0. `docs/man/1/tar.html` exists; `docs/data/index.js` replaced the sample.

- [ ] **Step 7: Verify in browser** (`preview_start` name `manpages`):
  1. Home page count now shows the real count (thousands).
  2. Search `tar`, press Enter → lands on `man/1/tar.html`; page shows styled content, TOC lists NAME/DESCRIPTION/…, header search still works from the page.
  3. On the tar page, a SEE ALSO cross-reference link navigates to another existing page.
  4. `preview_network` shows **no external-origin requests**; console has no errors.

- [ ] **Step 8: Commit** (sample corpus is committed; the full corpus later replaces it)

```
git add build/build_site.py build/templates build/test_build_site.py docs/man docs/data
git commit -m "feat: site generator with xr rewriting, toc, index, validation"
```

---

### Task 7: fetch.sh — package indexes and deb downloads

**Files:**
- Create: `build/fetch.sh`

**Interfaces:**
- Produces, under `<cache-dir>`: `indexes/` (Contents/Packages), `manpkgs.txt` (main packages shipping man pages), `download.tsv` (`pkg<TAB>pool-filename<TAB>sha256`), `debs/*.deb`, `fetch-failures.log`. Consumed by `unpack.sh` (Task 8).
- Env knobs: `MIRROR` (default `http://archive.ubuntu.com/ubuntu`), `SUITES` (default `noble noble-updates`), `PKG_LIMIT` (0 = all), `JOBS` (default 8).
- Verified URLs: `dists/noble/Contents-amd64.gz` (suite-level; per-component does NOT exist) and `dists/noble/main/binary-amd64/Packages.gz`. Contents rows: `usr/share/man/man1/tar.1.gz  utils/tar` — the last field is comma-separated `section/pkg` for main, `universe/section/pkg` for universe, so **main = qualifier with exactly 2 slash-separated parts**.

- [ ] **Step 1: Write `build/fetch.sh`**

```bash
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
```

- [ ] **Step 2: Test with a 25-package limit**

Run:
```
wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages && PKG_LIMIT=25 bash build/fetch.sh "$HOME/manbuild/cache"'
```
Expected: `packages:` several thousand; `to download:` slightly fewer (some Contents packages aren't in main Packages — fine); 25 debs downloaded; `failures: 0`. Contents files are large (~40 MB gz each) — the index step takes a couple of minutes.

- [ ] **Step 3: Verify a deb actually contains man pages**

Run:
```
wsl.exe -d Ubuntu-22.04 -- bash -c 'd=$(ls $HOME/manbuild/cache/debs/*.deb | head -1); echo "$d"; dpkg-deb --fsys-tarfile "$d" | tar -t | grep usr/share/man | head -5'
```
Expected: man page paths listed.

- [ ] **Step 4: Commit**

```
git add build/fetch.sh
git commit -m "feat: fetch.sh — Contents/Packages parsing, verified parallel deb downloads"
```

---

### Task 8: unpack.sh + limited end-to-end pipeline

**Files:**
- Create: `build/unpack.sh`, `build/run_all.sh`

**Interfaces:**
- `unpack.sh <cache-dir> <workdir>`: extracts `usr/share/man/man[1-9]*` from every cached deb into `<workdir>/extracted/usr/share/man` (consumed by `extract.sh`). Known limitation (accepted): when two packages ship the same page path, last extraction wins silently.
- `run_all.sh <cache-dir> <workdir> <repo-docs-path>`: fetch → unpack → extract → convert → build_site → copy generated output into the repo. One entry point for full or limited builds (honors `PKG_LIMIT`).

- [ ] **Step 1: Write `build/unpack.sh`**

```bash
#!/usr/bin/env bash
# unpack.sh — extract usr/share/man from every cached .deb into one tree.
# usage: unpack.sh <cache-dir> <workdir>
set -euo pipefail
CACHE=${1:?usage: unpack.sh <cache-dir> <workdir>}
WORK=${2:?usage: unpack.sh <cache-dir> <workdir>}
CACHE=$(readlink -f "$CACHE"); mkdir -p "$WORK"; WORK=$(readlink -f "$WORK")
DEST=$WORK/extracted
rm -rf "$DEST"; mkdir -p "$DEST"
export DEST

one() {
  dpkg-deb --fsys-tarfile "$1" 2>/dev/null \
    | tar -x -C "$DEST" --wildcards './usr/share/man/man[1-9]*' 2>/dev/null || true
}
export -f one

ls "$CACHE"/debs/*.deb | xargs -P "$(nproc)" -n 1 bash -c 'one "$1"' _
echo "==> extracted files: $(find "$DEST/usr/share/man" -type f -o -type l 2>/dev/null | wc -l)"
```

- [ ] **Step 2: Write `build/run_all.sh`**

```bash
#!/usr/bin/env bash
# run_all.sh — full pipeline: fetch -> unpack -> extract -> convert -> build -> copy.
# usage: run_all.sh <cache-dir> <workdir> <repo-docs-path>
# env:   PKG_LIMIT etc. pass through to fetch.sh
set -euo pipefail
CACHE=${1:?usage: run_all.sh <cache-dir> <workdir> <repo-docs>}
WORK=${2:?}
DOCS=${3:?}
HERE=$(dirname "$(readlink -f "$0")")

bash "$HERE/fetch.sh" "$CACHE"
bash "$HERE/unpack.sh" "$CACHE" "$WORK"
bash "$HERE/extract.sh" "$WORK/extracted/usr/share/man" "$WORK"
bash "$HERE/convert.sh" "$WORK"

OUT=$WORK/out
rm -rf "$OUT"; mkdir -p "$OUT"
python3 "$HERE/build_site.py" --work "$WORK" --out "$OUT"

echo "==> copying generated site into $DOCS"
rm -rf "$DOCS/man" "$DOCS/data"
cp -r "$OUT/man" "$OUT/data" "$DOCS/"
echo "==> done: $(find "$DOCS/man" -name '*.html' | wc -l) pages in $DOCS/man"
```

- [ ] **Step 3: Limited end-to-end run (200 packages)**

Run (background — takes ~10–20 min):
```
wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages && PKG_LIMIT=200 bash build/run_all.sh "$HOME/manbuild/cache" "$HOME/manbuild/work" /mnt/c/Users/Matt/Documents/manpages/docs'
```
Expected: each stage prints its summary; build_site exits 0 with `errors=0`; docs/man repopulated from the 200-package corpus.

- [ ] **Step 4: Browser spot-check** — search for a page from the limited corpus, open it, confirm styling + links (as Task 6 Step 7).

- [ ] **Step 5: Commit**

```
git add build/unpack.sh build/run_all.sh
git commit -m "feat: unpack.sh and run_all.sh pipeline entry point"
```

---

### Task 9: Full corpus build and commit

**Files:**
- Modify: `docs/man/**`, `docs/data/index.js` (regenerated at full scale)
- Create: `build/smoke_test.py`

**Interfaces:**
- Consumes: the whole pipeline (Tasks 4–8).
- Produces: the final committed site.

- [ ] **Step 1: Check WSL disk space** — need ~15 GB free in `$HOME` (`wsl.exe -d Ubuntu-22.04 -- df -h /home`). If short, stop and tell the user.

- [ ] **Step 2: Write `build/smoke_test.py`**

```python
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
```

- [ ] **Step 3: Full build, in background** (multi-hour: ~5–8 GB of debs)

Run with `run_in_background: true`:
```
wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages && PKG_LIMIT=0 JOBS=12 bash build/run_all.sh "$HOME/manbuild/cache" "$HOME/manbuild/work" /mnt/c/Users/Matt/Documents/manpages/docs > "$HOME/manbuild/full-build.log" 2>&1'
```
Monitor via the log file. Expected final lines: build_site summary with `errors=0` and the copy count (~15–20k pages). Review `$HOME/manbuild/work/site-report.txt` and `fetch-failures.log`; a handful of fetch failures is acceptable (note them), systematic failure is not.

- [ ] **Step 4: Run smoke test**

Run: `wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages && python3 build/smoke_test.py docs'`
Expected: `checked 200 of ~15000+ pages, 0 bad`, exit 0.

- [ ] **Step 5: Re-run search tests against real index size** (sanity: file loads, format valid)

Run: `wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages && node -e "global.window={};require(\"./docs/data/index.js\");var db=window.MANDB;console.log(\"pages:\",db.pages.length,\"aliases:\",db.aliases.length);var sc=require(\"./docs/assets/search-core.js\");var t=Date.now();for(var i=0;i<100;i++)sc.search(db,\"tar\",30);console.log(\"100 searches:\",Date.now()-t,\"ms\");"'`
Expected: pages ≥ 10000; 100 searches well under 1000 ms total.

- [ ] **Step 6: Browser verification at full scale** — search latency while typing feels instant; open several pages (`tar`, `systemd.unit`, a section-3 libc page); TOC and cross-links work; no console errors; no external requests.

- [ ] **Step 7: Commit the full corpus** (large commit; git add may take minutes)

```
git add build/smoke_test.py docs/man docs/data
git commit -m "feat: full ubuntu noble main corpus (pre-rendered pages + index)"
```

---

### Task 10: README + optional release workflow

**Files:**
- Create: `README.md`, `.github/workflows/release-zip.yml`

**Interfaces:**
- README documents: what this is, how to enable Pages (air-gapped GHES included), how to refresh the corpus, licensing notes.
- The workflow is **optional and public-side only** — the air-gapped instance never needs it.

- [ ] **Step 1: Write `README.md`**

```markdown
# manpages — offline linux manual

A lightning-fast man-page lookup site. The entire site — ~15–20k pre-rendered
Ubuntu 24.04 (noble, main) man pages, search index, fonts, styling — is static
files committed to this repo under `docs/`. It makes **zero network calls**:
no CDNs, no external fonts, no analytics. It works on an air-gapped GitHub
Enterprise instance and even opened straight from disk.

## Deploy (any GitHub / GitHub Enterprise)

1. Push this repo.
2. Settings → Pages → Source: **Deploy from a branch** → branch `main`, folder `/docs`.
3. Done. No Actions, no build step, no internet access required on the server.

## Local / offline use

Open `docs/index.html` directly in a browser, or serve it:
`python3 -m http.server --directory docs`. A zip of `docs/` is a complete
portable copy (see the optional release workflow).

## Keyboard shortcuts

`/` focus search · `↑` `↓` navigate results · `Enter` open · `Esc` clear.
Theme toggle (dark/light) is in the header; it follows your OS preference by default.

## Refreshing the corpus (internet-connected side only)

Requires WSL/Linux with `mandoc groff man-db curl dpkg-dev` installed:

    bash build/run_all.sh ~/manbuild/cache ~/manbuild/work "$(pwd)/docs"
    python3 build/smoke_test.py docs
    git add docs && git commit -m "chore: refresh corpus"

`PKG_LIMIT=200` limits the package count for a quick test run. Downloaded debs
are cached in `~/manbuild/cache` and reused on the next refresh.

## How it works

- `build/fetch.sh` finds every Ubuntu main package shipping man pages (via the
  archive `Contents` index) and downloads just those debs (sha256-verified).
- `build/unpack.sh` + `build/extract.sh` pull out English pages (sections 1–9),
  resolving `.so`/symlink aliases instead of duplicating pages.
- `build/convert.sh` renders each page with `mandoc -T html`
  (fallbacks: groff, then escaped `<pre>`; build aborts if >2% hit `<pre>`).
- `build/build_site.py` wraps pages in the app shell, links `name(section)`
  cross-references that exist in the corpus, and emits `docs/data/index.js` —
  a ~2 MB name+description index loaded as a script (works on `file://`).
- Search is ~100 lines of dependency-free JS (`docs/assets/search-core.js`).

## Licenses

- Man page content: belongs to the respective upstream Ubuntu packages (GPL and
  other free licenses) — see each page's footer/source package.
- Styling: [terminal-workbench-design-system](https://github.com/Real-Fruit-Snacks/terminal-workbench-design-system) tokens (MIT), vendored in `docs/assets/tokens.css`.
- Font: JetBrains Mono (OFL 1.1), vendored in `docs/assets/fonts/`.
```

- [ ] **Step 2: Write `.github/workflows/release-zip.yml`**

```yaml
# Optional, public-GitHub-side only: zips docs/ into a Release asset so the
# site can be carried into an air-gapped network as a single file.
name: release-zip
on:
  workflow_dispatch:
permissions:
  contents: write
jobs:
  zip:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd docs && zip -qr ../manpages-site.zip .
      - run: gh release create "site-$(date +%Y%m%d-%H%M)" manpages-site.zip --notes "Full static site zip — unzip and open index.html, or serve the folder."
        env:
          GH_TOKEN: ${{ github.token }}
```

- [ ] **Step 3: Commit**

```
git add README.md .github/workflows/release-zip.yml
git commit -m "docs: README and optional release-zip workflow"
```

---

### Task 11: Final verification pass

**Files:** none (verification only)

- [ ] **Step 1: Full test suite**

Run:
```
wsl.exe -d Ubuntu-22.04 -- bash -c 'cd /mnt/c/Users/Matt/Documents/manpages && node build/test_search.js && (cd build && python3 -m unittest test_build_site) && python3 build/smoke_test.py docs'
```
Expected: all pass.

- [ ] **Step 2: Zero-network audit** — with the preview server running, load home + one man page, then `preview_network`: every request URL must be `localhost:8321`. Grep the generated output for absolute URLs as a static check:

Run: `Grep pattern "(src|href)=\"https?://" over docs/ (glob *.html, head_limit 20)`
Expected: no hits in index.html/404.html/man pages (mandoc `.UR`-generated *text* links to external sites inside page content are acceptable — they load nothing; only `src=`/`link href=` resource loads matter, and there must be none).

- [ ] **Step 3: `file://` check** — open `docs/index.html` via the browser tools with a `file://` URL; search must work (index.js is a script tag, not fetch).

- [ ] **Step 4: Repo size sanity**

Run: `git count-objects -vH`
Expected: pack size well under 1 GB.

- [ ] **Step 5: Report** — summarize page count, repo size, fallback rate, any fetch failures; remind the user: push to GitHub → Settings → Pages → `main`/`docs`.
