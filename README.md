# gta6-race-rss

Unofficial RSS 2.0 feed of the [updates log](https://vuyp.github.io/gta6-pc-race/#updates)
of the GTA VI PC race site, which has no feed of its own.

**Feed URL:** `https://krys600.github.io/gta6-race-rss/feed.xml`

## How it works

- `scripts/build_feed.py` (Python standard library only) downloads the live page from
  `https://raw.githubusercontent.com/vuyp/gta6-pc-race/main/index.html`, parses every
  `<li class="log__row">` in `<section id="updates">`, and writes the 60 most recent
  entries to `feed.xml`. It exits with an error if no entry is found.
- `.github/workflows/update-feed.yml` runs every 15 minutes (and on demand) and commits
  `feed.xml` only when its content changed, ignoring `lastBuildDate`.
- GitHub Pages serves the repository root.

## Local run

```sh
python3 scripts/build_feed.py                       # live page -> feed.xml
python3 scripts/build_feed.py page.html out.xml     # local file
```
