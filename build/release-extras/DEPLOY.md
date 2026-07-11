# Hosting this bundle

This folder is the complete manpages site — every file needed to host it.
No build step, no internet access, no dependencies.

## Open it directly
Double-click `index.html`. Everything works from disk.

## Any web server
Serve this folder. Examples:

    python3 -m http.server 8000
    npx serve .
    nginx: root /path/to/this/folder;

## GitHub / GitHub Enterprise Pages
1. Create a repo, put these files in a `docs/` folder (or use the source
   repo: https://github.com/Real-Fruit-Snacks/manpages).
2. Settings → Pages → Deploy from a branch → your branch, `/docs`
   (or `/ (root)` if you put the files at the repo root).

## GitLab / self-hosted GitLab Pages
1. Create a repo and push this folder's contents to the default branch —
   including the `.gitlab-ci.yml` shipped in this bundle.
2. GitLab Pages publishes automatically (the job just copies files).

## What's inside
- `index.html`, `about.html`, `browse/` — search, about, section browsing
- `man/` — pre-rendered man pages (Ubuntu 24.04 main + universe)
- `assets/`, `data/` — styling, fonts, scripts, search index (all local)
- `sw.js`, `manifest.webmanifest` — offline caching / installable app
- `.gitlab-ci.yml` — GitLab Pages publishing for this exact layout
