export default function Sidebar({ id, open, policies, onNew, onClose }) {
  return (
    <>
      <div className={`scrim ${open ? "show" : ""}`} onClick={onClose} aria-hidden="true" />
      <aside id={id} className={`sidebar ${open ? "open" : ""}`} aria-label="Policies">
        <button className="btn btn-new" onClick={onNew}>
          <span aria-hidden="true">＋</span> New conversation
        </button>

        <p className="note">
          Each question is answered on its own. Include the details you need in every question; PolicyPal doesn't remember earlier messages.
        </p>

        <h2 className="sidebar-heading">Policies in the knowledge base</h2>
        {policies === null ? (
          <p className="muted small">The policy list couldn't be loaded.</p>
        ) : policies.length === 0 ? (
          <p className="muted small">Loading…</p>
        ) : (
          <ul className="policy-list">
            {policies.map((p) => (
              <li key={p.document_id}>
                <a href={p.source_url} target="_blank" rel="noopener noreferrer">
                  <span className="policy-id">{p.document_id}</span>
                  <span className="policy-title">{p.title}</span>
                </a>
              </li>
            ))}
          </ul>
        )}
        <a className="manage-link" href="/admin">
          Manage policies →
        </a>
        <p className="muted small fineprint">Acme Corp is fictional. All policies are synthetic documents created for this project.</p>
      </aside>
    </>
  );
}
