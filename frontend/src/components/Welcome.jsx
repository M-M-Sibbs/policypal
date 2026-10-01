export default function Welcome({ examples, onPick, disabled }) {
  return (
    <section className="welcome" aria-labelledby="welcome-title">
      <h2 id="welcome-title">Ask about Acme Corp's policies</h2>
      <p>
        PolicyPal searches the company handbook and policies, answers only from what they say, and shows the passages it used. If the
        policies don't cover your question, it will tell you instead of guessing.
      </p>
      {examples.length > 0 && (
        <>
          <h3 className="examples-heading">Try one of these</h3>
          <ul className="examples">
            {examples.map((q) => (
              <li key={q}>
                <button className="example" onClick={() => onPick(q)} disabled={disabled}>
                  {q}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
