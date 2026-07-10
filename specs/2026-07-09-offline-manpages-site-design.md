# Offline Man-Page Lookup Site — Design

**Date:** 2026-07-09
**Status:** Approved

> Note: specs live in `specs/` (not the skill-default `docs/superpowers/specs/`) because
> `docs/` is reserved as the GitHub Pages publish root.

## Goal

A lightning-fast Linux man-page lookup tool published as a GitHub Pages site. The repo is
fully self-contained: it can be pushed to an air-gapped GitHub Enterprise instance and
served via Pages "deploy from branch" with **zero network calls, zero external resources,
and zero build steps** on the serving side. Styling follows the
[terminal-workbench-design-system](https://github.com/Real-Fruit-Snacks/terminal-workbench-design-system)
(vendored, not linked).

## Non-goals

- Full-text search inside page bodies (name + NAME-description search only).
- Multiple distros/versions (single corpus: Ubuntu 24.04 LTS `main`).
- Server-side anything. The site is purely static files.

## Repo layout

```
manpages/
├── README.md
├── specs/                  ← design/plan documents (not published)
├── build/                  ← reproducible pipeline; runs in WSL on the internet side only
│   ├── fetch.sh            ← download Ubuntu package indexes + only the .debs that ship man pages
│   ├── extract.sh          ← unpack /usr/share/man (English, sections 1–8), resolve aliases
│   ├── convert.sh          ← mandoc → HTML fragments; groff fallback; <pre> last resort
│   └── build_site.py       ← wrap fragments in app-shell template, emit search index, validate
└── docs/                   ← the ENTIRE published site, committed to git
    ├── index.html          ← search home
    ├── 404.html
    ├── assets/
    │   ├── tokens.css      ← vendored terminal-workbench tokens (dark + light)
    │   ├── app.css
    │   ├── app.js
    │   └── fonts/          ← JetBrains Mono woff2 (OFL license, committed)
    ├── data/index.js       ← search index as a JS file (works on file:// too)
    └── man/<section>/<name>.html   ← one pre-rendered page each (e.g. man/1/tar.html)
```

GitHub Pages setting: deploy from branch, `/docs` folder. Works identically on github.io
and GHES. All asset/link paths are relative so the site works under any base path and via
`file://` from a release zip.

## Corpus & build pipeline

- **Source:** Ubuntu 24.04 LTS (`noble` + `noble-updates`), `main` component,
  amd64 — roughly 6,000 packages, ~15–20k man pages after dedup.
- `fetch.sh` parses the archive `Contents-amd64` index to find only packages shipping
  `usr/share/man`, then downloads those `.deb`s directly from the pool into a local cache
  (`build/cache/`, gitignored). Refreshes are incremental (skip already-cached debs).
- `extract.sh` unpacks only `usr/share/man/man[1-8]` English pages
  (`man/` and `man/en*/`), skipping localized trees. Alias pages (`.so` includes and
  symlinks — e.g. every bash builtin → `bash.1`) are resolved to their canonical page and
  recorded as **index aliases**, not duplicate HTML.
- `convert.sh` renders each page with `mandoc -T html` (fragment output). Failures fall
  back to `groff -mandoc -Thtml`, then to escaped plain text in `<pre>`. Every failure is
  logged to a conversion report; the build aborts if more than 2% of pages fail mandoc AND groff (i.e. land in the `<pre>` fallback).
- `build_site.py` wraps each fragment in the app-shell template, rewrites cross-references
  (`grep(1)` patterns and SEE ALSO entries) into relative links **only when the target
  exists in the corpus**, generates `data/index.js`, `index.html`, and `404.html`, and runs
  validation (below).

Build cost: one-time ~10 GB deb download into WSL cache, a few hours unattended. The
generated `docs/` tree (~150–300 MB packed in git) is committed.

## Search

- Index entries: `name`, `section`, one-line NAME description, aliases, path.
  ~2 MB raw / ~500 KB gzip-served, shipped as `data/index.js` and loaded with
  `<script defer>` on **every** page so search works from anywhere. Cached after first load.
- Matching is in-memory: case-insensitive substring with prefix/exact-name boosting
  (exact name > name prefix > name substring > alias > description substring). Results
  render on each keystroke; at ~20k entries this is well under a millisecond.
- Shipped as `.js` (assigns a global) rather than fetched `.json` so it also works when the
  site is opened from disk (`file://` blocks `fetch()` in Chrome).

## UI

- **Theme:** dark graphite default (`--twb-bg-0: #090c0d`, accent `#63f2ab`), light mode
  via `prefers-color-scheme` plus a manual toggle persisted in `localStorage`
  (`data-theme` attribute, per the design system).
- **Keyboard-first:** `/` focuses search, `↑/↓` move selection, `Enter` opens, `Esc`
  clears/unfocuses. Section number shown as ANSI-tinted badges.
- **Home:** centered terminal-style prompt, results list under it, short hint line of
  keyboard shortcuts.
- **Man page view:** sticky mini-header (site name + search box), page title as
  `name(section)`, on-page TOC of section headings, auto-linked cross-references. The
  rendered content is server-side (build-time) HTML — fully readable with JS disabled.
- **Fonts:** JetBrains Mono (vendored woff2, OFL) with system monospace fallback. No UI
  font download — system sans stack for chrome per tokens.css fallbacks.

## Error handling

- Build: conversion failures logged + fallback chain (mandoc → groff → `<pre>`); the build
  aborts if any index entry points to a missing file or any generated link is dangling.
- Client: empty search shows shortcut hints; no matches shows a "no matches" state;
  `404.html` offers the search box.

## Verification

1. Build-time validation in `build_site.py` (index↔file integrity, dangling links,
   conversion report).
2. Smoke script: spot-check 200 random pages parse as HTML and contain a NAME heading.
3. Manual browser pass: search latency feel, arrow-key navigation, theme toggle, deep link
   to a page, JS-disabled readability, `file://` operation.

## Milestones

1. App shell + theme + search working against a small sample corpus (a handful of
   hand-fetched pages) — validates UX end to end.
2. Full pipeline: fetch/extract/convert at scale, alias resolution, validation.
3. Full corpus build, commit `docs/`, publish to GitHub Pages, verify live.
4. Optional: GitHub Actions workflow (public side only) to zip `docs/` into a Release.
