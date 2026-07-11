# Changelog

All notable changes to this project are documented here. Release assets: each
release attaches `manpages-site.zip`, the complete static site.

## [Unreleased]
- Release bundle now includes a ready-to-use `.gitlab-ci.yml` and `DEPLOY.md`
  hosting guide alongside the site files.

## [1.2.0] - 2026-07-11
- Corpus: Ubuntu 24.04 `universe` added alongside `main` — 58,464 pages and
  24,035 aliases (tmux, jq, htop, nmap, and 16,000+ more packages). Universe
  library-internals sections (2/3/4/9) are excluded to stay within GitHub
  Pages' 1 GB site limit; near-duplicate pages (e.g. per-architecture copies
  of the GCC manual) are deduplicated into search aliases.
- Provenance: every page footer shows its source package and version;
  `build/corpus-manifest.tsv` records the full mapping.
- Browse-by-section pages and an about page.
- Search: section filter syntax (`tar 5`, `tar.5`, bare `5`), match
  highlighting, recently-viewed chips on the home page.
- Accessibility: ARIA combobox search semantics, skip-to-content link.
- Installable PWA: web manifest, icons, versioned service worker with
  offline caching (stale-while-revalidate).
- Print stylesheet.
- Engineering: MIT LICENSE, this changelog, CI running the full test suite
  and a link audit on every push, tag-driven releases, link/img validation
  hardening, newline-safe pipeline for filenames with spaces, NTFS-safe
  lowercased section directories.

## [1.1.2] - 2026-07-10
- Prompt character moved inside the search box so the dropdown aligns with the input.
- Ghost speech bubbles on by default.

## [1.1.1] - 2026-07-10
- Removed the home-page hero subtitle line.

## [1.1.0] - 2026-07-10
- Ghost pet companion (ported from Real-Fruit-Snacks/obsidian-vault-publisher) with full settings:
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
