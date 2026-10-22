"""Map the model's [n] markers back to retrieved chunks and build citations
from trusted metadata only. The model chooses *which* evidence it used; the
backend supplies titles, snippets and URLs, so the model cannot invent a source."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .embeddings import content_tokens
from .generator import split_sentences
from .vectorstore import Hit

MARKER_RE = re.compile(r"\[(\d+)\]")
GROUPED_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)+)\]")


@dataclass
class CitationResult:
    answer: str
    citations: list[dict]
    dropped_markers: list[int]
    format_valid: bool = False


def citation_format_valid(answer: str, valid_ids: set[int]) -> bool:
    """Structural checks only, NOT semantic entailment or factual accuracy.

    Conservatively require citations on every text-bearing sentence/list item.
    Reject the entire output on unknown/malformed markers or uncited text;
    deleting a marker cannot repair its unsupported claim.
    """
    answer = normalise_markers(answer)
    remainder = MARKER_RE.sub('', answer)
    if '[' in remainder or ']' in remainder:
        return False
    units = split_sentences(answer)
    if not units:
        return False
    for unit in units:
        ids = {int(m.group(1)) for m in MARKER_RE.finditer(unit)}
        if not ids or not ids <= valid_ids:
            return False
        if not re.search(r'\w', MARKER_RE.sub('', unit)):
            return False
    return True


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
        # Match common morphological variants (approve/approval/approved)
        # without introducing question- or policy-specific rules.
        overlap = sum(any(t == c or (min(len(t), len(c)) >= 5 and
                      t[:min(len(t), len(c)) - 1] == c[:min(len(t), len(c)) - 1]) for t in tokens)
                      for c in claim_tokens)
        # Numeric bands can support a derived amount absent verbatim from the
        # answer. Do not penalise a range simply for having extra endpoints.
        lexical_length = sum(not re.search(r'\d', t) for t in tokens)
        score = overlap / (lexical_length ** 0.5 or 1.0)
        # Introductions alone cannot support a claim about a particular item.
        if sentence.endswith(':') and i + 1 < len(sentences):
            score *= 0.5
        if '|' in sentence and i + 1 < len(sentences) and '|' in sentences[i + 1] and (i == 0 or '|' not in sentences[i - 1]):
            score *= 0.5  # table header is context, not a data row
        if score > best_score:
            best_i, best_score = i, score
    first, last = best_i, best_i
    if sentences[best_i].endswith(':') and best_i + 1 < len(sentences):
        last += 1
    # Preserve the governing list introduction, or the column header for a
    # table row. Keep a contiguous excerpt so omissions are never concealed.
    for i in range(best_i - 1, -1, -1):
        if sentences[i].endswith(':'):
            first = i
            break
        if not ('|' in sentences[best_i] or sentences[i].endswith(';')):
            break
        if '|' in sentences[best_i] and '|' in sentences[i]:
            first = i
    start = chunk_text.find(sentences[first])
    end = chunk_text.find(sentences[last], start) + len(sentences[last])
    snippet = chunk_text[start:end]
    if len(snippet) > limit and first < best_i:
        # Keep both the governing context and selected item; explicitly mark
        # omitted intervening rows instead of truncating away the evidence.
        snippet = sentences[first] + '\n…\n' + sentences[best_i]
        return snippet
    # add the following sentence for context when there is room
    if best_i + 1 < len(sentences) and len(snippet) + 1 + len(sentences[best_i + 1]) <= limit:
        next_end = chunk_text.find(sentences[best_i + 1], end)
        if next_end >= 0 and last == best_i and first == best_i:
            candidate = chunk_text[start:next_end + len(sentences[best_i + 1])]
            if len(candidate) <= limit:
                snippet = candidate
    if len(snippet) > limit:
        cut = snippet[: limit - 1].rsplit(" ", 1)[0]
        snippet = cut + "…"
    return snippet


def snippet_is_verbatim(snippet: str, chunk_text: str) -> bool:
    parts = snippet.split('\n…\n')
    return bool(parts) and all(part.rstrip('…').strip() and part.rstrip('…') in chunk_text for part in parts)


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
        # Compound sentences can state several facts backed by different
        # passages of one chunk. Select evidence for each clause as well.
        claim_units = [unit for claim in (claims[new] or [claim_text])
                       for unit in re.split(r';\s*|,\s+and\s+', claim) if unit.strip()]
        excerpts = list(dict.fromkeys(best_snippet(chunk.text, claim, snippet_chars) for claim in claim_units))
        excerpts = [e for e in excerpts if not any(e != other and e in other for other in excerpts)]
        snippet = '\n…\n'.join(excerpts)
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
                "snippet": snippet,
                "snippet_truncated": any(excerpt.endswith('…') for excerpt in excerpts),
                "source_url": chunk.source_url,
                "url": chunk.source_url,
            }
        )
    return CitationResult(answer=clean_answer, citations=citations, dropped_markers=dropped,
                          format_valid=citation_format_valid(answer, valid))
