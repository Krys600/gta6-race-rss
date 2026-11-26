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

## Reliable scheduling (optional)

GitHub's `schedule` trigger is best effort: on low-traffic repositories, runs are often
delayed or skipped. For updates every 15 minutes, call the `workflow_dispatch` endpoint
from an external scheduler (for example cron-job.org):

- Method/URL: `POST https://api.github.com/repos/Krys600/gta6-race-rss/actions/workflows/update-feed.yml/dispatches`
- Headers: `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`,
  `Content-Type: application/json`
- Body: `{"ref":"main"}` (a successful call returns HTTP 204)
- Token: a fine-grained personal access token limited to this repository, with only
  **Actions: Read and write**. Store it in the scheduler, never in this repository.

The built-in `schedule` stays as a fallback; the `concurrency` group prevents overlapping runs.
