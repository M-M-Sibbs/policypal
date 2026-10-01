import { forwardRef } from "react";

const Composer = forwardRef(function Composer({ value, onChange, onSubmit, pending, maxChars }, ref) {
  const tooLong = value.length > maxChars;
  const empty = value.trim().length === 0;

  const onKeyDown = (e) => {
    // Enter sends, Shift+Enter adds a new line
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (!pending && !empty && !tooLong) onSubmit();
    }
  };

  return (
    <form
      className="composer"
      onSubmit={(e) => {
        e.preventDefault();
        if (!pending && !empty && !tooLong) onSubmit();
      }}
    >
      <label htmlFor="composer-input" className="composer-label">
        Ask a policy question
      </label>
      <div className="composer-row">
        <textarea
          id="composer-input"
          ref={ref}
          rows={2}
          value={value}
          placeholder="e.g. How many sick days do I get each year?"
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          aria-describedby="composer-help"
          aria-invalid={tooLong}
        />
        <button type="submit" className="btn btn-send" disabled={pending || empty || tooLong}>
          {pending ? "Waiting…" : "Send"}
        </button>
      </div>
      <div id="composer-help" className={`composer-help ${tooLong ? "error" : ""}`}>
        <span>Enter to send · Shift+Enter for a new line</span>
        <span>
          {value.length}/{maxChars}
        </span>
      </div>
    </form>
  );
});

export default Composer;
