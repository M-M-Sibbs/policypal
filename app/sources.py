"""Render registered policy documents for the /sources/<doc_id> route.

Only files listed in the manifest can be served; the document id is looked up,
never used to build a path. Headings get the same anchors the chunker records,
so citation links like /sources/POL-02#carry-over land on the cited section.
PDFs are served as-is so the browser viewer can honour #page=N."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import markdown

from .config import Settings
from .corpus import entry_path, read_corpus_file
from .parsing import FRONT_MATTER_RE, TXT_HEADER_RE, clean_html_soup, read_text_file, slugify

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · PolicyPal sources</title>
<style>
  :root {{ --ink:#1b2430; --muted:#5b6675; --line:#dde3ea; --accent:#0f766e; --bg:#f7f9fb; --hl:#fff4c2; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font:16px/1.65 "Source Serif 4", Georgia, serif; color:var(--ink); background:var(--bg); }}
  header {{ background:#fff; border-bottom:1px solid var(--line); padding:14px 20px; font-family: system-ui, sans-serif; }}
  header a {{ color:var(--accent); text-decoration:none; font-weight:600; }}
  .meta {{ color:var(--muted); font-size:14px; margin-top:4px; }}
  main {{ max-width:760px; margin:0 auto; padding:24px 20px 80px; background:#fff; min-height:100vh; }}
  h1,h2,h3 {{ font-family: system-ui, sans-serif; line-height:1.25; scroll-margin-top:16px; }}
  h2 {{ margin-top:2em; border-top:1px solid var(--line); padding-top:1em; }}
  :target {{ background:var(--hl); outline:6px solid var(--hl); border-radius:2px; }}
  table {{ border-collapse:collapse; width:100%; font-size:15px; margin:1em 0; display:block; overflow-x:auto; }}
  th,td {{ border:1px solid var(--line); padding:6px 10px; text-align:left; vertical-align:top; }}
  th {{ background:#f0f4f7; font-family: system-ui, sans-serif; }}
</style>
</head>
<body>
<header>
  <a href="/">← PolicyPal</a>
  <div class="meta">{doc_id} · {title} · version {version} · effective {effective_date} · source file {filename}</div>
</header>
<main>
{body}
</main>
</body>
</html>"""


def load_registry(settings: Settings) -> dict[str, dict]:
    """Documents in the current index (including runtime updates); falls back
    to the committed manifest before the first index build."""
    corpus = read_corpus_file(settings)
    if corpus is None:
        corpus = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    return {d["document_id"]: d for d in corpus["documents"]}


def _toc_slugify(value: str, separator: str) -> str:  # python-markdown signature
    return slugify(value)


def _render_markdownish(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["tables", "sane_lists", "toc"],
        extension_configs={"toc": {"slugify": _toc_slugify}},
    )


def _render_html(raw: str) -> str:
    soup = clean_html_soup(raw)
    root = soup.find("main") or soup.body or soup
    for heading in root.find_all(["h1", "h2", "h3"]):
        heading["id"] = slugify(heading.get_text(" "))
    for tag in root.find_all(True):  # drop inline event handlers / styles
        for attr in list(tag.attrs):
            if attr.startswith("on") or attr == "style":
                del tag.attrs[attr]
    return "".join(str(child) for child in root.children)


def resolve_source(settings: Settings, doc_id: str) -> tuple[str, Path | str] | None:
    """Return ("pdf", path) or ("html", rendered_page), or None if unknown."""
    entry = load_registry(settings).get(doc_id)
    if entry is None:
        return None
    path = entry_path(settings, entry)
    if not path.exists():
        return None
    if entry["format"] == "pdf":
        return "pdf", path
    raw = read_text_file(path)
    if entry["format"] == "md":
        m = FRONT_MATTER_RE.match(raw)
        body = _render_markdownish(raw[m.end():] if m else raw)
    elif entry["format"] == "txt":
        m = TXT_HEADER_RE.match(raw)
        if m and not re.search(r"^(doc_id|title)\s*:", m.group(1), re.M):
            m = None  # a ==== underline, not a metadata header
        body = _render_markdownish(raw[m.end():] if m else raw)
    else:
        body = _render_html(raw)
    page = PAGE_TEMPLATE.format(
        title=html.escape(entry["title"]),
        doc_id=html.escape(entry["document_id"]),
        version=html.escape(entry["version"]),
        effective_date=html.escape(entry["effective_date"]),
        filename=html.escape(entry["filename"]),
        body=body,
    )
    return "html", page


_ID_RE = re.compile(r"^[A-Za-z0-9-]{1,32}$")


def is_valid_doc_id(doc_id: str) -> bool:
    return bool(_ID_RE.match(doc_id))
