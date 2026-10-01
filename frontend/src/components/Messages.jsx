import { useRef, useState } from "react";
import { locationLabel, splitAnswer } from "../answerParts.js";

export function UserMessage({ text }) {
  return (
    <li className="msg msg-user">
      <span className="sr-only">You asked:</span>
      <p>{text}</p>
    </li>
  );
}

const REFUSAL_TITLES = {
  out_of_scope: "Outside the policies",
  insufficient_evidence: "Not covered by the policies",
};

const ERROR_TITLES = {
  invalid_request: "Please check your question",
  knowledge_base_unavailable: "Knowledge base unavailable",
  provider_error: "Answer service unavailable",
  provider_timeout: "The answer took too long",
  network_error: "Connection problem",
  internal_error: "Something went wrong",
};

export function AssistantMessage({ message, onRetry, retryDisabled }) {
  if (message.state === "pending") {
    return (
      <li className="msg msg-assistant" aria-busy="true">
        <div className="thinking">
          <span className="dot" />
          <span className="dot" />
          <span className="dot" />
          <span>Searching the policies and checking sources…</span>
        </div>
      </li>
    );
  }

  if (message.state === "error") {
    const { error } = message;
    return (
      <li className="msg msg-assistant">
        <div className="notice notice-error" role="alert">
          <strong>{ERROR_TITLES[error.status] || ERROR_TITLES.internal_error}</strong>
          <p>{error.message}</p>
          {error.retryable && (
            <button className="btn btn-ghost" onClick={onRetry} disabled={retryDisabled}>
              Retry
            </button>
          )}
        </div>
      </li>
    );
  }

  const { data } = message;
  if (data.status !== "answered") {
    return (
      <li className="msg msg-assistant">
        <div className="notice notice-refusal">
          <strong>{REFUSAL_TITLES[data.status] || "No answer"}</strong>
          <p>{data.answer}</p>
        </div>
        <Meta data={data} />
      </li>
    );
  }

  return (
    <li className="msg msg-assistant">
      <Answer data={data} />
      <Meta data={data} />
    </li>
  );
}

function Answer({ data }) {
  const [open, setOpen] = useState(() => new Set(data.citations.length ? [data.citations[0].id] : []));
  const cardRefs = useRef({});
  const ids = data.citations.map((c) => c.id);

  const focusCard = (id) => {
    setOpen((prev) => new Set(prev).add(id));
    const el = cardRefs.current[id];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      el.focus({ preventScroll: true });
    }
  };

  const toggle = (id) =>
    setOpen((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <>
      <p className="answer">
        {splitAnswer(data.answer, ids).map((part, i) =>
          part.type === "text" ? (
            <span key={i}>{part.value}</span>
          ) : (
            <button key={i} className="cite" onClick={() => focusCard(part.id)} aria-label={`Show source ${part.id}`}>
              {part.id}
            </button>
          ),
        )}
      </p>
      {data.truncated && <p className="muted small">This answer was shortened to stay within the length limit.</p>}

      <h3 className="sources-heading">Sources</h3>
      <ol className="sources">
        {data.citations.map((c) => (
          <li key={c.id} className="source-card" tabIndex={-1} ref={(el) => (cardRefs.current[c.id] = el)}>
            <button className="source-head" aria-expanded={open.has(c.id)} onClick={() => toggle(c.id)}>
              <span className="source-num">{c.id}</span>
              <span className="source-title">
                <strong>{c.title}</strong>
                <span className="muted"> · {locationLabel(c)}</span>
              </span>
              <span className="chev" aria-hidden="true">
                {open.has(c.id) ? "−" : "+"}
              </span>
            </button>
            {open.has(c.id) && (
              <div className="source-body">
                <blockquote>{c.snippet}</blockquote>
                <div className="source-foot">
                  <span className="muted small">
                    {c.document_id} · version {c.document_version}
                  </span>
                  <a href={c.source_url} target="_blank" rel="noopener noreferrer">
                    View source ↗
                  </a>
                </div>
              </div>
            )}
          </li>
        ))}
      </ol>
    </>
  );
}

function Meta({ data }) {
  return (
    <p className="meta">
      {(data.latency_ms / 1000).toFixed(1)} s · {data.provider}
    </p>
  );
}
