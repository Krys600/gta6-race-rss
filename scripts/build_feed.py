#!/usr/bin/env python3
"""Build an RSS 2.0 feed from the #updates section of the GTA VI PC race site.

Usage:
    python3 scripts/build_feed.py [SOURCE_HTML] [OUTPUT_XML]

SOURCE_HTML is optional: a local HTML file (for tests). When omitted, the
live page is downloaded from GitHub. OUTPUT_XML defaults to feed.xml.
Standard library only.
"""

import hashlib
import sys
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime
from html.parser import HTMLParser
from xml.sax.saxutils import escape

SOURCE_URL = "https://raw.githubusercontent.com/vuyp/gta6-pc-race/main/index.html"
SITE_URL = "https://vuyp.github.io/gta6-pc-race/"
ITEM_LINK = SITE_URL + "#updates"
FEED_TITLE = "GTA VI PC race - Updates"
FEED_DESCRIPTION = "Unofficial RSS feed of the updates log at " + ITEM_LINK
MAX_ITEMS = 60

# Elements that never have a closing tag; they must not affect depth tracking.
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


def has_class(attrs, name):
    classes = (dict(attrs).get("class") or "").split()
    return name in classes


class UpdatesParser(HTMLParser):
    """Collect entries from <li class="log__row"> inside <section id="updates">."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.entries = []
        self.depth = 0
        self.section_depth = None  # depth of <section id="updates">
        self.row_depth = None      # depth of the current <li class="log__row">
        self.row = None
        self.title_depth = None    # depth of <h3 class="t-card">
        self.points_depth = None   # depth of <ul class="points">
        self.point_depth = None    # depth of the current point <li>
        self.point_buf = None
        self.done = False          # True once the updates section has closed

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            return
        self.depth += 1
        if self.done:
            return
        attr = dict(attrs)

        if self.section_depth is None:
            if tag == "section" and attr.get("id") == "updates":
                self.section_depth = self.depth
            return

        if self.row is None:
            if tag == "li" and has_class(attrs, "log__row"):
                self.row_depth = self.depth
                self.row = {"datetime": None, "title": [], "points": []}
            return

        if tag == "time" and self.row["datetime"] is None and attr.get("datetime"):
            self.row["datetime"] = attr["datetime"]
        elif tag == "h3" and has_class(attrs, "t-card") and self.title_depth is None:
            self.title_depth = self.depth
        elif tag == "ul" and has_class(attrs, "points") and self.points_depth is None:
            self.points_depth = self.depth
        elif (tag == "li" and self.points_depth is not None
              and self.depth == self.points_depth + 1):
            self.point_depth = self.depth
            self.point_buf = []

    def handle_startendtag(self, tag, attrs):
        # Self-closing syntax (<br/>): no depth change.
        pass

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if self.section_depth is None or self.done:
            self.depth -= 1
            return

        if self.row is not None:
            if self.point_depth == self.depth:
                text = normalize("".join(self.point_buf))
                if text:
                    self.row["points"].append(text)
                self.point_depth = None
                self.point_buf = None
            elif self.points_depth == self.depth:
                self.points_depth = None
            elif self.title_depth == self.depth:
                self.title_depth = None
            elif self.row_depth == self.depth:
                self.finish_row()

        if self.section_depth == self.depth:
            self.done = True  # section closed; ignore the rest
        self.depth -= 1

    def handle_data(self, data):
        if self.row is None:
            return
        if self.title_depth is not None:
            self.row["title"].append(data)
        if self.point_buf is not None:
            self.point_buf.append(data)

    def finish_row(self):
        row = self.row
        self.row = None
        self.row_depth = self.title_depth = self.points_depth = None
        self.point_depth = self.point_buf = None
        title = normalize("".join(row["title"]))
        if not row["datetime"] or not title:
            print(f"warning: skipping incomplete row (datetime={row['datetime']!r}, "
                  f"title={title!r})", file=sys.stderr)
            return
        self.entries.append({
            "datetime": row["datetime"],
            "date": parse_datetime(row["datetime"]),
            "title": title,
            "points": row["points"],
        })


def normalize(text):
    """Collapse whitespace, including non-breaking spaces."""
    return " ".join(text.replace(" ", " ").split())


def parse_datetime(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_html(source):
    if source:
        with open(source, encoding="utf-8") as fh:
            return fh.read()
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "gta6-race-rss"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def parse_entries(html):
    parser = UpdatesParser()
    parser.feed(html)
    parser.close()
    return parser.entries


def build_rss(entries, now):
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "<channel>",
        f"<title>{escape(FEED_TITLE)}</title>",
        f"<link>{escape(ITEM_LINK)}</link>",
        f"<description>{escape(FEED_DESCRIPTION)}</description>",
        "<language>en</language>",
        f"<lastBuildDate>{format_datetime(now, usegmt=True)}</lastBuildDate>",
        "<ttl>15</ttl>",
    ]
    for entry in entries:
        guid = hashlib.sha1(
            f"{entry['datetime']}|{entry['title']}".encode("utf-8")).hexdigest()
        if entry["points"]:
            body = "<ul>" + "".join(
                f"<li>{escape(p)}</li>" for p in entry["points"]) + "</ul>"
        else:
            body = ""
        out += [
            "<item>",
            f"<title>{escape(entry['title'])}</title>",
            f"<link>{escape(ITEM_LINK)}</link>",
            f'<guid isPermaLink="false">{guid}</guid>',
            f"<pubDate>{format_datetime(entry['date'], usegmt=True)}</pubDate>",
            f"<description>{escape(body)}</description>",
            "</item>",
        ]
    out += ["</channel>", "</rss>", ""]
    return "\n".join(out)


def main(argv):
    source = argv[1] if len(argv) > 1 else None
    output = argv[2] if len(argv) > 2 else "feed.xml"

    html = load_html(source)
    entries = parse_entries(html)
    if not entries:
        sys.exit("error: no entries found in <section id=\"updates\"> "
                 "(no <li class=\"log__row\"> with <time datetime> and "
                 "<h3 class=\"t-card\">). The page structure may have changed.")

    entries.sort(key=lambda e: e["date"], reverse=True)
    print(f"Parsed {len(entries)} entries; keeping {min(len(entries), MAX_ITEMS)}.")
    entries = entries[:MAX_ITEMS]

    xml = build_rss(entries, datetime.now(timezone.utc))
    with open(output, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(xml)
    print(f"Wrote {output}.")


if __name__ == "__main__":
    main(sys.argv)
