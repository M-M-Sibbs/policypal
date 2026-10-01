"""Section-aware chunking.

Sections are split by headings first. A section that fits in `chunk_tokens`
becomes one chunk; a longer section is split into windows of `chunk_tokens`
with `chunk_overlap` tokens of overlap. Tokens are approximated by
whitespace-separated words, which is close enough for a 500-token budget and
keeps chunking independent of any particular model tokenizer.

Windows never cross a section boundary, and each chunk records the pages it
spans so PDF citations can link to the exact page."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .parsing import ParsedDocument


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    document_version: str
    title: str
    section: str
    anchor: str
    page_start: int | None
    page_end: int | None
    text: str
    source_url: str
    source_path: str
    format: str
    corpus_version: str = ""

    def metadata(self) -> dict:
        """Chroma metadata must be str/int/float/bool; None becomes -1 / ''."""
        meta = asdict(self)
        meta.pop("text")
        meta["page_start"] = self.page_start if self.page_start is not None else -1
        meta["page_end"] = self.page_end if self.page_end is not None else -1
        return meta

    @classmethod
    def from_metadata(cls, meta: dict, text: str) -> "Chunk":
        data = dict(meta)
        for key in ("page_start", "page_end"):
            value = data.get(key)
            data[key] = None if value in (None, -1, "") else int(value)
        fields = cls.__dataclass_fields__
        return cls(text=text, **{k: v for k, v in data.items() if k in fields and k != "text"})


def source_url(doc_id: str, anchor: str, page: int | None) -> str:
    """Links are built only from trusted metadata, never from model output."""
    if page is not None:
        return f"/sources/{doc_id}#page={page}"
    return f"/sources/{doc_id}#{anchor}"


def chunk_document(doc: ParsedDocument, chunk_tokens: int = 500, chunk_overlap: int = 75) -> list[Chunk]:
    if chunk_overlap >= chunk_tokens:
        raise ValueError("chunk_overlap must be smaller than chunk_tokens")
    chunks: list[Chunk] = []
    version = doc.meta["version"]
    for s_idx, section in enumerate(doc.sections):
        # (word, page) pairs so a window knows which pages it covers
        words: list[tuple[str, int | None]] = []
        for block in section.blocks:
            block_words = block.text.split()
            if not block_words:
                continue
            # keep block boundaries as newlines in the reconstructed text
            words.extend((w, block.page) for w in block_words[:-1])
            words.append((block_words[-1] + "\n", block.page))
        if not words:
            continue
        step = chunk_tokens - chunk_overlap
        starts = [0] if len(words) <= chunk_tokens else list(range(0, len(words) - chunk_overlap, step))
        for part, start in enumerate(starts):
            window = words[start : start + chunk_tokens]
            pages = [p for _, p in window if p is not None]
            page_start = min(pages) if pages else None
            page_end = max(pages) if pages else None
            text = " ".join(w for w, _ in window).replace("\n ", "\n").strip()
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}-v{version}-s{s_idx:02d}-c{part:02d}",
                    document_id=doc.doc_id,
                    document_version=version,
                    title=doc.meta["title"],
                    section=section.heading,
                    anchor=section.anchor,
                    page_start=page_start,
                    page_end=page_end,
                    text=text,
                    source_url=source_url(doc.doc_id, section.anchor, page_start),
                    source_path=doc.path.name,
                    format=doc.format,
                )
            )
    return chunks
