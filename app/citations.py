"""Map the model's [n] markers back to retrieved chunks and build citations
from trusted metadata only. The model chooses *which* evidence it used; the
backend supplies titles, snippets and URLs, so the model cannot invent a source."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .embeddings import content_tokens
from .generator import split_sentences
from .vectorstore import Hit

MARKER_RE = re.compile(r"\[(\d{1,2})\]")
GROUPED_RE = re.compile(r"\[(\d{1,2}(?:\s*,\s*\d{1,2})+)\]")


@dataclass
class CitationResult:
    answer: str
    citations: list[dict]
    dropped_markers: list[int]


def normalise_markers(answer: str) -> str:
    """Turn grouped markers like [1, 3] into [1][3]."""
    return GROUPED_RE.sub(lambda m: "".join(f"[{n.strip()}]" for n in m.group(1).split(",")), answer)


def best_snippet(chunk_text: str, claim_text: str, limit: int) -> str:
    """Pick the passage sentence that best supports the claim. The snippet is an
    exact excerpt of the stored chunk text (optionally cut with an ellipsis)."""
    claim_tokens = set(content_tokens(claim_text))
    sentences = split_sentences(chunk_text) or [chunk_text.strip()]
    best_i, best_score = 0, -1.0
    for i, sentence in enumerate(sentences):
        tokens = set(content_tokens(sentence))
        score = len(claim_tokens & tokens) / (len(tokens) ** 0.5 or 1.0)
        if score > best_score:
            best_i, best_score = i, score
    snippet = sentences[best_i]
    # add the following sentence for context when there is room
    if best_i + 1 < len(sentences) and len(snippet) + 1 + len(sentences[best_i + 1]) <= limit:
        candidate = f"{snippet} {sentences[best_i + 1]}"
        if candidate in chunk_text:
            snippet = candidate
    if len(snippet) > limit:
        cut = snippet[: limit - 1].rsplit(" ", 1)[0]
        snippet = cut + "…"
    return snippet


def snippet_is_verbatim(snippet: str, chunk_text: str) -> bool:
    return snippet.rstrip("…") in chunk_text


def build_citations(answer: str, hits: list[Hit], snippet_chars: int = 300) -> CitationResult:
    answer = normalise_markers(answer)
    valid = set(range(1, len(hits) + 1))

    order: list[int] = []
    dropped: list[int] = []
    for m in MARKER_RE.finditer(answer):
        n = int(m.group(1))
        if n in valid:
            if n not in order:
                order.append(n)
        elif n not in dropped:
            dropped.append(n)

    # Renumber in order of first appearance so marker [k] is the k-th card.
    renumber = {old: new for new, old in enumerate(order, start=1)}

    def replace(m: re.Match) -> str:
        n = int(m.group(1))
        return f"[{renumber[n]}]" if n in renumber else ""

    clean_answer = MARKER_RE.sub(replace, answer)
    clean_answer = re.sub(r"\s+([.,;:])", r"\1", re.sub(r"[ \t]{2,}", " ", clean_answer)).strip()

    # Which sentences cite which marker, to choose the most relevant snippet.
    claims: dict[int, list[str]] = {n: [] for n in renumber.values()}
    for sentence in split_sentences(clean_answer):
        for m in MARKER_RE.finditer(sentence):
            n = int(m.group(1))
            if n in claims:
                claims[n].append(MARKER_RE.sub("", sentence))

    citations = []
    for old in order:
        new = renumber[old]
        chunk = hits[old - 1].chunk
        claim_text = " ".join(claims[new]) or clean_answer
        citations.append(
            {
                "id": new,
                "ref": new,
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "doc_id": chunk.document_id,
                "document_version": chunk.document_version,
                "title": chunk.title,
                "section": chunk.section,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "snippet": best_snippet(chunk.text, claim_text, snippet_chars),
                "source_url": chunk.source_url,
                "url": chunk.source_url,
            }
        )
    return CitationResult(answer=clean_answer, citations=citations, dropped_markers=dropped)
