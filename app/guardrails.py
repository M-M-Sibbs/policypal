"""Input validation, refusal handling and the output-length cap."""
from __future__ import annotations

import re

from .generator import INSUFFICIENT, split_sentences

# The refusal wording comes from the product spec (FR-9).
REFUSAL_OUT_OF_SCOPE = "I can only answer about our policies."
REFUSAL_INSUFFICIENT = (
    "I can only answer about our policies, and the policy documents I found don't cover this question. "
    "Try rephrasing it, or contact the People team."
)
REFUSAL_UNCITED = (
    "I can only answer about our policies, and I couldn't produce an answer that is backed by a citation. "
    "Please rephrase your question."
)

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class InvalidQuestion(ValueError):
    pass


def validate_question(raw, max_chars: int) -> str:
    if not isinstance(raw, str):
        raise InvalidQuestion("The request must include a 'question' string.")
    question = _CONTROL_CHARS.sub("", raw).strip()
    if not question:
        raise InvalidQuestion("Please enter a question.")
    if len(question) > max_chars:
        raise InvalidQuestion(f"Questions must be {max_chars} characters or fewer (received {len(question)}).")
    return question


def is_refusal(text: str) -> bool:
    cleaned = text.strip().strip(".").strip()
    if not cleaned:
        return True
    if INSUFFICIENT in cleaned.upper().replace(" ", "_"):
        return True
    return cleaned.lower().startswith(REFUSAL_OUT_OF_SCOPE.lower().rstrip("."))


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", re.sub(r"\[\d+\]", "", text)))


def enforce_word_cap(answer: str, max_words: int) -> tuple[str, bool]:
    """Verify the cap after generation (token limits do not guarantee it).
    Shorten only at sentence boundaries so no citation is split from its claim."""
    if word_count(answer) <= max_words:
        return answer, False
    kept, total = [], 0
    for sentence in split_sentences(answer):
        n = word_count(sentence)
        if total + n > max_words:
            break
        kept.append(sentence)
        total += n
    return " ".join(kept), True
