"""Render the PDF policies (POL-06, POL-07, POL-12) from their Markdown sources.

The PDFs in data/policies/ are committed, so this script only needs to run when
a source in data/pdf_sources/ changes:

    python scripts/build_pdfs.py

Each heading becomes a PDF bookmark (outline entry). The ingestion parser uses
those bookmarks to recover section boundaries and real page numbers. A running
header and footer are added on purpose so that the cleaning step has real
headers/footers to remove.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "data" / "pdf_sources"
OUT_DIR = ROOT / "data" / "policies"

FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)


def parse_front_matter(text: str) -> tuple[dict, str]:
    m = FRONT_MATTER.match(text)
    if not m:
        raise ValueError("missing front-matter")
    meta = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"')
    return meta, text[m.end():]


def inline(md: str) -> str:
    md = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    md = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", md)
    return md


class BookmarkedDoc(SimpleDocTemplate):
    """Adds a PDF outline entry for every heading paragraph."""

    def afterFlowable(self, flowable):  # noqa: N802 (reportlab API)
        level = getattr(flowable, "_heading_level", None)
        if level is None:
            return
        key = f"h{id(flowable)}"
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(flowable._heading_text, key, level=level, closed=False)


def build(src: Path) -> Path:
    meta, body = parse_front_matter(src.read_text(encoding="utf-8"))
    out = OUT_DIR / (src.stem + ".pdf")

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=18, spaceAfter=10)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13.5, spaceBefore=10, spaceAfter=6)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=11.5, spaceBefore=8, spaceAfter=4)
    body_style = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10.5, leading=14.5, alignment=TA_LEFT)
    meta_style = ParagraphStyle("Meta", parent=body_style, fontSize=9.5, textColor="#444444")

    story = []
    # Visible header block mirrors the front-matter of the md/txt/html policies.
    for key in ("doc_id", "title", "version", "effective_date", "category"):
        story.append(Paragraph(f"{key}: {inline(meta[key])}", meta_style))
    story.append(Spacer(1, 12))

    bullets: list[str] = []

    def flush_bullets():
        if bullets:
            story.append(
                ListFlowable(
                    [ListItem(Paragraph(inline(b), body_style), leftIndent=12) for b in bullets],
                    bulletType="bullet",
                    start="•",
                    leftIndent=14,
                )
            )
            story.append(Spacer(1, 4))
            bullets.clear()

    for block in re.split(r"\n\s*\n", body.strip()):
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        first = lines[0]
        heading = re.match(r"^(#{1,3})\s+(.*)$", first)
        if heading and len(lines) == 1:
            flush_bullets()
            level = len(heading.group(1)) - 1
            text = heading.group(2).strip()
            para = Paragraph(inline(text), (h1, h2, h3)[level])
            para._heading_level = level
            para._heading_text = text
            story.append(para)
            continue
        if all(ln.lstrip().startswith("- ") for ln in lines):
            bullets.extend(ln.lstrip()[2:] for ln in lines)
            continue
        flush_bullets()
        story.append(Paragraph(inline(" ".join(lines)), body_style))
        story.append(Spacer(1, 4))
    flush_bullets()

    header_text = f"Acme Corp  |  {meta['doc_id']} {meta['title']}  |  Internal"

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillGray(0.4)
        canvas.drawString(inch, LETTER[1] - 0.6 * inch, header_text)
        canvas.drawRightString(LETTER[0] - inch, 0.55 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = BookmarkedDoc(
        str(out),
        pagesize=LETTER,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
        title=meta["title"],
        author="Acme Corp (synthetic policy for PolicyPal)",
        subject=meta["doc_id"],
        keywords=f"doc_id={meta['doc_id']};version={meta['version']};effective_date={meta['effective_date']}",
        invariant=1,  # deterministic output (fixed IDs/timestamps)
    )
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return out


def main() -> int:
    sources = sorted(SRC_DIR.glob("*.md"))
    for src in sources:
        out = build(src)
        print(f"built {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
