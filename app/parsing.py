"""Parse and clean the four supported policy formats (md, txt, html, pdf) into a
common structure: a document with metadata and an ordered list of sections.

Each section keeps its heading, an anchor used by source links, and its text
blocks together with the physical page they came from (PDF only; other
formats have no pages, so page is None)."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_SUFFIXES = {".md", ".txt", ".html", ".htm", ".pdf"}
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*#*\s*$")
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
TXT_HEADER_RE = re.compile(r"^(.*?)\n=+\s*\n", re.S)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def normalise_ws(text: str) -> str:
    text = text.replace(" ", " ").replace("‑", "-")
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Block:
    text: str
    page: int | None = None


@dataclass
class Section:
    heading: str
    level: int
    anchor: str
    blocks: list[Block] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(b.text for b in self.blocks)

    @property
    def page_start(self) -> int | None:
        pages = [b.page for b in self.blocks if b.page is not None]
        return min(pages) if pages else None

    @property
    def page_end(self) -> int | None:
        pages = [b.page for b in self.blocks if b.page is not None]
        return max(pages) if pages else None


@dataclass
class ParsedDocument:
    path: Path
    format: str
    meta: dict
    sections: list[Section]
    page_count: int | None = None

    @property
    def doc_id(self) -> str:
        return self.meta["doc_id"]


def _parse_key_values(block: str) -> dict:
    meta = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def _clean_markdown_inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text


def _markdown_body_to_sections(body: str, title: str) -> list[Section]:
    """Shared by .md and .txt: both use #/## headings and blank-line paragraphs."""
    sections: list[Section] = []
    current = Section(heading=title, level=1, anchor=slugify(title))
    paragraph: list[str] = []

    def flush_paragraph():
        if paragraph:
            text = normalise_ws(" ".join(paragraph))
            if text:
                current.blocks.append(Block(text))
            paragraph.clear()

    for raw in body.splitlines():
        line = raw.rstrip()
        heading = HEADING_RE.match(line)
        if heading:
            flush_paragraph()
            if current.blocks or current.level > 1 or sections:
                sections.append(current)
            text = _clean_markdown_inline(heading.group(2))
            current = Section(heading=text, level=len(heading.group(1)), anchor=slugify(text))
            continue
        if not line.strip():
            flush_paragraph()
            continue
        stripped = line.strip()
        if re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?", stripped):
            continue  # markdown table separator row
        if stripped.startswith("|"):
            flush_paragraph()
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            current.blocks.append(Block(normalise_ws(_clean_markdown_inline(" | ".join(cells)))))
            continue
        if re.match(r"^([-*]|\d+\.)\s+", stripped):
            flush_paragraph()  # each list item becomes its own block
            paragraph.append(_clean_markdown_inline(re.sub(r"^[-*]\s+", "", stripped)))
            flush_paragraph()
            continue
        paragraph.append(_clean_markdown_inline(stripped))
    flush_paragraph()
    sections.append(current)
    return [s for s in sections if s.blocks]


def parse_markdown(path: Path) -> ParsedDocument:
    text = path.read_text(encoding="utf-8")
    m = FRONT_MATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path.name}: missing front-matter block")
    meta = _parse_key_values(m.group(1))
    body = text[m.end():]
    return ParsedDocument(path, "md", meta, _markdown_body_to_sections(body, meta["title"]))


def parse_text(path: Path) -> ParsedDocument:
    text = path.read_text(encoding="utf-8")
    m = TXT_HEADER_RE.match(text)
    if not m:
        raise ValueError(f"{path.name}: missing header block terminated by a ==== line")
    meta = _parse_key_values(m.group(1))
    body = text[m.end():]
    return ParsedDocument(path, "txt", meta, _markdown_body_to_sections(body, meta["title"]))


def clean_html_soup(html: str):
    """Return a BeautifulSoup tree with navigation, scripts and chrome removed."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe", "form"]):
        tag.decompose()
    return soup


def parse_html(path: Path) -> ParsedDocument:
    from bs4 import BeautifulSoup

    raw = path.read_text(encoding="utf-8")
    head = BeautifulSoup(raw, "html.parser")
    meta = {
        tag.get("name"): tag.get("content", "").strip()
        for tag in head.find_all("meta")
        if tag.get("name")
    }
    if "doc_id" not in meta:
        raise ValueError(f"{path.name}: missing <meta name=doc_id>")
    soup = clean_html_soup(raw)
    root = soup.find("main") or soup.body or soup

    sections: list[Section] = []
    current = Section(heading=meta["title"], level=1, anchor=slugify(meta["title"]))
    for el in root.find_all(["h1", "h2", "h3", "p", "li", "tr"]):
        if el.name in {"h1", "h2", "h3"}:
            if current.blocks:
                sections.append(current)
            heading = normalise_ws(el.get_text(" "))
            current = Section(heading=heading, level=int(el.name[1]), anchor=slugify(heading))
        elif el.name == "tr":
            cells = [normalise_ws(c.get_text(" ")) for c in el.find_all(["td", "th"])]
            if cells:
                current.blocks.append(Block(" | ".join(cells)))
        else:
            if el.name == "p" and el.find_parent("li"):
                continue
            text = normalise_ws(el.get_text(" "))
            if text:
                current.blocks.append(Block(text))
    if current.blocks:
        sections.append(current)
    return ParsedDocument(path, "html", meta, sections)


def _flatten_outline(reader, outline, level=0, out=None):
    out = [] if out is None else out
    for item in outline:
        if isinstance(item, list):
            _flatten_outline(reader, item, level + 1, out)
        else:
            out.append((normalise_ws(item.title), level, reader.get_destination_page_number(item) + 1))
    return out


def parse_pdf(path: Path) -> ParsedDocument:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    info = reader.metadata or {}
    meta = {"title": str(info.get("/Title", path.stem)), "doc_id": str(info.get("/Subject", ""))}
    for part in str(info.get("/Keywords", "")).split(";"):
        if "=" in part:
            k, _, v = part.partition("=")
            meta[k.strip()] = v.strip()

    pages = [(page.extract_text() or "").splitlines() for page in reader.pages]

    # Remove running headers/footers: lines that recur (ignoring digits) on at
    # least half the pages are boilerplate, e.g. "Acme Corp | POL-06 ... " and "Page 3".
    def norm(line: str) -> str:
        return re.sub(r"\d+", "#", normalise_ws(line))

    counts = Counter(norm(l) for lines in pages for l in set(lines) if l.strip())
    min_repeats = max(2, len(pages) // 2)
    boilerplate = {k for k, v in counts.items() if v >= min_repeats}

    # Visible header block on page 1 ("doc_id: POL-06" ...) supplies metadata.
    if pages:
        keep = []
        for line in pages[0]:
            m = re.match(r"^(doc_id|title|version|effective_date|category):\s*(.+)$", line.strip())
            if m:
                meta.setdefault(m.group(1), m.group(2).strip())
                if m.group(1) in {"doc_id", "version", "effective_date", "category"}:
                    meta[m.group(1)] = m.group(2).strip()
            else:
                keep.append(line)
        pages[0] = keep

    outline = _flatten_outline(reader, reader.outline)
    sections: list[Section] = []
    current: Section | None = None
    next_heading = 0
    buffer: list[str] = []
    buffer_page = 1

    def flush():
        nonlocal buffer
        if buffer and current is not None:
            text = normalise_ws(" ".join(buffer))
            if text:
                current.blocks.append(Block(text, buffer_page))
        buffer = []

    for page_no, lines in enumerate(pages, start=1):
        flush()  # never let a block span pages, so page numbers stay exact
        for line in lines:
            clean = normalise_ws(line)
            if not clean or norm(clean) in boilerplate:
                continue
            if next_heading < len(outline):
                title, level, heading_page = outline[next_heading]
                if clean == title and heading_page == page_no:
                    flush()
                    if current is not None and current.blocks:
                        sections.append(current)
                    current = Section(heading=title, level=level + 1, anchor=slugify(title))
                    next_heading += 1
                    continue
            if current is None:
                current = Section(heading=meta["title"], level=1, anchor=slugify(meta["title"]))
            if clean.startswith("•"):
                flush()
                clean = clean.lstrip("• ").strip()
            if not buffer:
                buffer_page = page_no
            buffer.append(clean)
    flush()
    if current is not None and current.blocks:
        sections.append(current)
    return ParsedDocument(path, "pdf", meta, sections, page_count=len(reader.pages))


def parse_document(path: Path) -> ParsedDocument:
    suffix = path.suffix.lower()
    if suffix == ".md":
        doc = parse_markdown(path)
    elif suffix == ".txt":
        doc = parse_text(path)
    elif suffix in {".html", ".htm"}:
        doc = parse_html(path)
    elif suffix == ".pdf":
        doc = parse_pdf(path)
    else:
        raise ValueError(f"unsupported file type: {path.name}")
    for key in ("doc_id", "title", "version", "effective_date"):
        if not doc.meta.get(key):
            raise ValueError(f"{path.name}: missing metadata field {key!r}")
    return doc
