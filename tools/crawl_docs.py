"""UNVERIFIED crawler for the docs.cybcube.com content API (the same app serves docs.int01.internal.cybcube.com).

The site is a React shell; articles come from `https://api.docs.<host>/cms/...` and every call needs the app's login
session. This script was written from the endpoint templates found in the app bundle and has NOT been run against the
API, because no session was available when it was written. Expect to adjust the JSON field names on first use.

    DOCS_API_TOKEN="<value of the Authorization header your browser sends on /cms/ calls>" \\
    python tools/crawl_docs.py --host docs.cybcube.com --roots 594,599,595,605,615,585 --out corpus/product-docs

Each article is written as Markdown with front matter (id, title, collection=product-docs, url). HTML is reduced to
text with headings kept. Nothing is sent anywhere except the docs API.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys
from pathlib import Path

import httpx

TAG = re.compile(r"<[^>]+>")
HEAD = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.I | re.S)
BLOCK = re.compile(r"</(p|div|li|tr|section|article|table)>", re.I)


def html_to_markdown(body: str) -> str:
    body = HEAD.sub(lambda m: "\n" + "#" * int(m.group(1)) + " " + TAG.sub("", m.group(2)).strip() + "\n", body)
    body = BLOCK.sub("\n", body)
    text = html.unescape(TAG.sub("", body))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:80]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="docs.cybcube.com")
    ap.add_argument("--roots", required=True, help="comma-separated root category ids, e.g. 594,599")
    ap.add_argument("--out", default="corpus/product-docs")
    a = ap.parse_args()
    token = os.environ.get("DOCS_API_TOKEN")
    if not token:
        print("DOCS_API_TOKEN is not set", file=sys.stderr)
        return 2
    api = f"https://api.{a.host}"
    headers = {"Authorization": token if token.lower().startswith("bearer ") else f"Bearer {token}", "Accept": "application/json", "Origin": f"https://{a.host}"}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    with httpx.Client(timeout=30, headers=headers) as c:
        for root in [r.strip() for r in a.roots.split(",") if r.strip()]:
            cat = c.get(f"{api}/cms/categories/{root}", params={"root": root})
            cat.raise_for_status()
            data = cat.json()
            articles = data.get("articles") or data.get("data", {}).get("articles") or []
            section = slugify(data.get("slug") or data.get("name") or f"root-{root}")
            for art in articles:
                slug = art.get("slug") or slugify(art.get("title", ""))
                r = c.get(f"{api}/cms/categories/{root}/articles/{slug}", params={"root": root})
                if r.status_code != 200:
                    print(f"skip {slug}: {r.status_code}", file=sys.stderr)
                    continue
                d = r.json()
                body = d.get("content") or d.get("body") or d.get("html") or ""
                title = d.get("title") or art.get("title") or slug
                url = f"https://{a.host}/{section}/{slug}?root={root}"
                md = f"---\nid: doc-{slugify(title)}\ntitle: {title}\ncollection: product-docs\nurl: {url}\nfictional: false\n---\n\n{html_to_markdown(body)}\n"
                (out / f"{slugify(title)}.md").write_text(md, encoding="utf-8")
                written += 1
    print(f"wrote {written} articles to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
