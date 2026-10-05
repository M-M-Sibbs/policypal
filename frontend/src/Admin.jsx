import { useCallback, useEffect, useRef, useState } from "react";
import {
  adminStatus,
  listPolicies,
  loadToken,
  reindexPolicies,
  removePolicy,
  resetPolicies,
  saveToken,
  uploadPolicy,
} from "./adminApi.js";

const ORIGIN_LABEL = { original: "Original", uploaded: "Added", replaced: "Updated" };
const EMPTY_FIELDS = { doc_id: "", title: "", version: "", effective_date: "", category: "" };

export default function Admin() {
  const [status, setStatus] = useState(null); // {enabled, max_upload_mb, allowed_types}
  const [token, setToken] = useState(loadToken);
  const [data, setData] = useState(null); // {policies, hidden, index}
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState(null); // {kind: "ok"|"error", text}

  const refresh = useCallback(
    async (tok = token) => {
      try {
        setData(await listPolicies(tok));
        return true;
      } catch (err) {
        if (err.httpStatus === 401) {
          saveToken("");
          setToken("");
          setNotice({ kind: "error", text: "That admin token was not accepted." });
        } else {
          setNotice({ kind: "error", text: err.message });
        }
        return false;
      }
    },
    [token],
  );

  useEffect(() => {
    adminStatus()
      .then(setStatus)
      .catch(() => setStatus({ enabled: false, error: true }));
  }, []);

  useEffect(() => {
    if (status?.enabled && token) refresh(token);
  }, [status, token, refresh]);

  const run = async (label, action) => {
    setBusy(label);
    setNotice(null);
    try {
      const result = await action();
      const idx = result.index;
      const detail = idx
        ? ` Index: ${idx.document_count} policies, ${idx.chunk_count} chunks (${idx.embedded_chunks} re-embedded) in ${idx.build_seconds}s.`
        : "";
      setNotice({ kind: "ok", text: `${result.message}${detail}` });
      await refresh();
      return true;
    } catch (err) {
      setNotice({ kind: "error", text: err.message });
      return false;
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="admin">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">P</span>
          <div>
            <h1>PolicyPal · Manage policies</h1>
            <p className="tagline">Add, update or remove the policies PolicyPal answers from</p>
          </div>
        </div>
        <a className="btn btn-ghost admin-back" href="/">
          ← Back to chat
        </a>
      </header>

      <main className="admin-main">
        <div className="sr-only" role="status" aria-live="polite">
          {busy ? `${busy}…` : notice?.text || ""}
        </div>

        {status === null ? (
          <p className="muted">Loading…</p>
        ) : !status.enabled ? (
          <section className="card">
            <h2>Policy management is turned off</h2>
            <p>
              {status.error
                ? "The admin service could not be reached."
                : "Set the ADMIN_TOKEN environment variable on the server (for example in Render → Environment) and restart, then come back to this page."}
            </p>
          </section>
        ) : !token ? (
          <TokenForm
            notice={notice}
            onSubmit={async (tok) => {
              setNotice(null);
              if (await refresh(tok)) {
                saveToken(tok);
                setToken(tok);
              }
            }}
          />
        ) : (
          <>
            {notice && (
              <div className={`notice ${notice.kind === "ok" ? "notice-ok" : "notice-error"}`} role={notice.kind === "error" ? "alert" : undefined}>
                <p>{notice.text}</p>
              </div>
            )}

            <UploadCard
              policies={data?.policies || []}
              maxMb={status.max_upload_mb}
              busy={busy}
              onUpload={(file, fields) => run("Uploading and re-indexing", () => uploadPolicy(token, file, fields))}
            />

            <section className="card">
              <div className="card-head">
                <h2>Policies in the knowledge base</h2>
                {data?.index && (
                  <span className="muted small">
                    {data.index.document_count} policies · {data.index.chunk_count} chunks · corpus {data.index.corpus_version}
                  </span>
                )}
              </div>
              {!data ? (
                <p className="muted">Loading…</p>
              ) : (
                <div className="table-wrap">
                  <table className="policy-table">
                    <thead>
                      <tr>
                        <th scope="col">ID</th>
                        <th scope="col">Title</th>
                        <th scope="col">Version</th>
                        <th scope="col">Effective</th>
                        <th scope="col">Status</th>
                        <th scope="col">
                          <span className="sr-only">Actions</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.policies.map((p) => (
                        <tr key={p.document_id}>
                          <td className="mono">{p.document_id}</td>
                          <td>
                            <a href={p.source_url} target="_blank" rel="noopener noreferrer">
                              {p.title}
                            </a>
                            <div className="muted small">{p.filename}</div>
                          </td>
                          <td>{p.version}</td>
                          <td>{p.effective_date}</td>
                          <td>
                            <span className={`badge badge-${p.origin}`}>{ORIGIN_LABEL[p.origin] || p.origin}</span>
                          </td>
                          <td className="actions">
                            <button
                              className="btn btn-ghost btn-small"
                              disabled={Boolean(busy)}
                              onClick={() => {
                                const msg =
                                  p.origin === "replaced"
                                    ? `Remove the uploaded version of ${p.document_id} and go back to the original?`
                                    : `Remove ${p.document_id} (${p.title}) from the knowledge base?`;
                                if (window.confirm(msg)) run("Removing and re-indexing", () => removePolicy(token, p.document_id));
                              }}
                            >
                              {p.origin === "replaced" ? "Revert" : "Remove"}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {data?.hidden?.length > 0 && <p className="muted small">Removed originals: {data.hidden.join(", ")}</p>}
            </section>

            <section className="card">
              <h2>Maintenance</h2>
              <p className="muted">
                Changes made here take effect immediately. On a free hosting plan they last until the service restarts or redeploys,
                which restores the original policies. To make a change permanent, add the file to <code>data/policies/</code> in the
                repository (see README).
              </p>
              <div className="button-row">
                <button className="btn btn-ghost" disabled={Boolean(busy)} onClick={() => run("Re-indexing", () => reindexPolicies(token))}>
                  Re-index now
                </button>
                <button
                  className="btn btn-danger"
                  disabled={Boolean(busy)}
                  onClick={() => {
                    if (window.confirm("Remove all uploads and restore the original policies?")) run("Restoring original policies", () => resetPolicies(token));
                  }}
                >
                  Reset to original policies
                </button>
                <button
                  className="btn btn-ghost"
                  onClick={() => {
                    saveToken("");
                    setToken("");
                    setData(null);
                    setNotice(null);
                  }}
                >
                  Sign out
                </button>
              </div>
            </section>
          </>
        )}
        {busy && (
          <div className="busy" aria-hidden="true">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
            <span>{busy}…</span>
          </div>
        )}
      </main>
    </div>
  );
}

function TokenForm({ onSubmit, notice }) {
  const [value, setValue] = useState("");
  return (
    <section className="card narrow">
      <h2>Sign in</h2>
      <p className="muted">Enter the admin token configured on the server (ADMIN_TOKEN).</p>
      {notice?.kind === "error" && (
        <div className="notice notice-error" role="alert">
          <p>{notice.text}</p>
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim()) onSubmit(value.trim());
        }}
      >
        <label htmlFor="admin-token" className="field-label">
          Admin token
        </label>
        <div className="composer-row">
          <input id="admin-token" type="password" autoComplete="current-password" value={value} onChange={(e) => setValue(e.target.value)} />
          <button type="submit" className="btn btn-send" disabled={!value.trim()}>
            Sign in
          </button>
        </div>
      </form>
    </section>
  );
}

function UploadCard({ policies, maxMb, busy, onUpload }) {
  const [file, setFile] = useState(null);
  const [fields, setFields] = useState(EMPTY_FIELDS);
  const [showDetails, setShowDetails] = useState(false);
  const fileRef = useRef(null);
  const tooBig = file && file.size > maxMb * 1024 * 1024;
  const target = policies.find((p) => p.document_id === fields.doc_id.trim().toUpperCase());

  const set = (k) => (e) => setFields((f) => ({ ...f, [k]: e.target.value }));

  return (
    <section className="card">
      <h2>Add or update a policy</h2>
      <p className="muted">
        Upload a Markdown, text, HTML or PDF file (up to {maxMb} MB). To <strong>update</strong> a policy, choose it under “Replaces”
        or use the same <code>doc_id</code> in the file. Anything not given is taken from the file, and an updated policy’s version goes
        up automatically. <a href="/api/admin/template">Download a template</a>.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (!file || tooBig || busy) return;
          const ok = await onUpload(file, fields);
          if (ok) {
            setFile(null);
            setFields(EMPTY_FIELDS);
            if (fileRef.current) fileRef.current.value = "";
          }
        }}
      >
        <div className="form-grid">
          <div>
            <label htmlFor="policy-file" className="field-label">
              Policy file
            </label>
            <input
              id="policy-file"
              ref={fileRef}
              type="file"
              accept=".md,.txt,.html,.htm,.pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              aria-invalid={Boolean(tooBig)}
            />
            {tooBig && <p className="field-error">This file is larger than {maxMb} MB.</p>}
          </div>
          <div>
            <label htmlFor="policy-target" className="field-label">
              Replaces
            </label>
            <select id="policy-target" value={target ? target.document_id : ""} onChange={(e) => setFields((f) => ({ ...f, doc_id: e.target.value }))}>
              <option value="">New policy (or use the file’s doc_id)</option>
              {policies.map((p) => (
                <option key={p.document_id} value={p.document_id}>
                  {p.document_id} — {p.title} (v{p.version})
                </option>
              ))}
            </select>
          </div>
        </div>

        <button type="button" className="link-button" aria-expanded={showDetails} onClick={() => setShowDetails((s) => !s)}>
          {showDetails ? "Hide" : "Set"} title, version and date (optional)
        </button>
        {showDetails && (
          <div className="form-grid four">
            <Field id="f-docid" label="Policy ID" placeholder="POL-13" value={fields.doc_id} onChange={set("doc_id")} />
            <Field id="f-title" label="Title" placeholder="From the file" value={fields.title} onChange={set("title")} />
            <Field id="f-version" label="Version" placeholder={target ? `auto (after ${target.version})` : "1.0"} value={fields.version} onChange={set("version")} />
            <Field id="f-date" label="Effective date" type="date" value={fields.effective_date} onChange={set("effective_date")} />
            <Field id="f-cat" label="Category" placeholder="General" value={fields.category} onChange={set("category")} />
          </div>
        )}

        <div className="button-row">
          <button type="submit" className="btn btn-send" disabled={!file || tooBig || Boolean(busy)}>
            {busy ? "Working…" : target ? `Update ${target.document_id}` : "Add policy"}
          </button>
        </div>
      </form>
    </section>
  );
}

function Field({ id, label, ...props }) {
  return (
    <div>
      <label htmlFor={id} className="field-label">
        {label}
      </label>
      <input id={id} type="text" {...props} />
    </div>
  );
}
