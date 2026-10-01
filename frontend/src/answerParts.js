// Split an answer like "Carry over 5 days [1][2]." into text and citation
// tokens. Rendering tokens as React elements (never innerHTML) keeps model
// output from injecting markup.

const MARKER = /\[(\d{1,2})\]/g;

export function splitAnswer(answer, validIds) {
  const valid = new Set(validIds);
  const parts = [];
  let last = 0;
  for (const match of answer.matchAll(MARKER)) {
    const id = Number(match[1]);
    if (match.index > last) parts.push({ type: "text", value: answer.slice(last, match.index) });
    if (valid.has(id)) parts.push({ type: "cite", id });
    last = match.index + match[0].length;
  }
  if (last < answer.length) parts.push({ type: "text", value: answer.slice(last) });
  return parts;
}

export function locationLabel(citation) {
  const { page_start: start, page_end: end } = citation;
  if (start == null) return citation.section;
  const pages = end && end !== start ? `pages ${start}–${end}` : `page ${start}`;
  return `${citation.section} · ${pages}`;
}
