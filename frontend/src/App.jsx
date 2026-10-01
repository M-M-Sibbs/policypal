import { useCallback, useEffect, useRef, useState } from "react";
import { askQuestion, fetchPolicies } from "./api.js";
import Sidebar from "./components/Sidebar.jsx";
import Welcome from "./components/Welcome.jsx";
import Composer from "./components/Composer.jsx";
import { AssistantMessage, UserMessage } from "./components/Messages.jsx";

let nextId = 1;
const newId = () => nextId++;

export default function App() {
  const [policies, setPolicies] = useState([]);
  const [examples, setExamples] = useState([]);
  const [maxChars, setMaxChars] = useState(2000);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [statusText, setStatusText] = useState("");
  const scrollRef = useRef(null);
  const composerRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    fetchPolicies()
      .then((data) => {
        setPolicies(data.policies);
        setExamples(data.examples);
        setMaxChars(data.max_question_chars);
      })
      .catch(() => setPolicies(null));
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKey = (e) => e.key === "Escape" && setMenuOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  const send = useCallback(
    async (text, { retryOf } = {}) => {
      const question = text.trim();
      if (!question || pending) return; // no duplicate sends while waiting
      setPending(true);
      setStatusText("Searching the policies…");
      const assistantId = retryOf ?? newId();
      setMessages((prev) => {
        if (retryOf) {
          return prev.map((m) => (m.id === retryOf ? { ...m, state: "pending", error: null } : m));
        }
        return [...prev, { id: newId(), role: "user", text: question }, { id: assistantId, role: "assistant", state: "pending", question }];
      });
      if (!retryOf) setDraft("");

      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const data = await askQuestion(question, { signal: controller.signal });
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, state: "done", data } : m)));
        setStatusText(data.status === "answered" ? `Answer ready with ${data.citations.length} source${data.citations.length === 1 ? "" : "s"}.` : "PolicyPal could not answer from the policies.");
      } catch (error) {
        if (error?.name === "AbortError") return;
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, state: "error", error } : m)));
        setStatusText(error.message);
        // keep the question so the user doesn't have to retype it
        setDraft((d) => d || question);
      } finally {
        abortRef.current = null;
        setPending(false);
        composerRef.current?.focus();
      }
    },
    [pending],
  );

  const newConversation = () => {
    abortRef.current?.abort();
    setMessages([]);
    setDraft("");
    setPending(false);
    setMenuOpen(false);
    setStatusText("Started a new conversation.");
    composerRef.current?.focus();
  };

  return (
    <div className="app">
      <a className="skip-link" href="#composer-input">Skip to question box</a>
      <header className="topbar">
        <button
          className="menu-toggle"
          aria-expanded={menuOpen}
          aria-controls="sidebar"
          onClick={() => setMenuOpen((o) => !o)}
        >
          <span aria-hidden="true">☰</span>
          <span className="sr-only">Policies menu</span>
        </button>
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">P</span>
          <div>
            <h1>PolicyPal</h1>
            <p className="tagline">Answers from company policies, with sources</p>
          </div>
        </div>
      </header>

      <div className="layout">
        <Sidebar id="sidebar" open={menuOpen} policies={policies} onNew={newConversation} onClose={() => setMenuOpen(false)} />

        <main className="chat" aria-label="Conversation">
          <div className="scroll" ref={scrollRef}>
            {messages.length === 0 ? (
              <Welcome examples={examples} onPick={(q) => send(q)} disabled={pending} />
            ) : (
              <ol className="messages">
                {messages.map((m) =>
                  m.role === "user" ? (
                    <UserMessage key={m.id} text={m.text} />
                  ) : (
                    <AssistantMessage key={m.id} message={m} onRetry={() => send(m.question, { retryOf: m.id })} retryDisabled={pending} />
                  ),
                )}
              </ol>
            )}
          </div>
          <div className="sr-only" role="status" aria-live="polite">
            {statusText}
          </div>
          <Composer ref={composerRef} value={draft} onChange={setDraft} onSubmit={() => send(draft)} pending={pending} maxChars={maxChars} />
        </main>
      </div>
    </div>
  );
}
