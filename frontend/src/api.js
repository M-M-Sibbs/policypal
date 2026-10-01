// Talks to the Flask API. Every non-2xx response is turned into a typed
// error object so the UI can show the right state (invalid input, knowledge
// base unavailable, provider failure with retry, network failure).

const RETRYABLE = new Set(["provider_error", "provider_timeout", "knowledge_base_unavailable", "network_error", "internal_error"]);

export async function askQuestion(question, { signal } = {}) {
  let resp;
  try {
    resp = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal,
    });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw { status: "network_error", message: "Couldn't reach PolicyPal. Check your connection and retry.", retryable: true };
  }
  let body = null;
  try {
    body = await resp.json();
  } catch {
    body = null;
  }
  if (!resp.ok || !body) {
    const status = body?.status || "internal_error";
    throw {
      status,
      message: body?.message || `The server returned an unexpected response (HTTP ${resp.status}).`,
      retryable: RETRYABLE.has(status),
      httpStatus: resp.status,
    };
  }
  return body;
}

export async function fetchPolicies() {
  const resp = await fetch("/api/policies");
  if (!resp.ok) throw new Error("Could not load the policy list");
  return resp.json();
}
