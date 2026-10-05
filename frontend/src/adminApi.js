// Calls to the token-protected /api/admin endpoints. The token is kept in
// sessionStorage (cleared when the tab closes) so a page refresh does not
// sign the admin out; storage failures (private mode) are tolerated.

const KEY = "policypal-admin-token";

export function loadToken() {
  try {
    return sessionStorage.getItem(KEY) || "";
  } catch {
    return "";
  }
}

export function saveToken(token) {
  try {
    if (token) sessionStorage.setItem(KEY, token);
    else sessionStorage.removeItem(KEY);
  } catch {
    /* storage unavailable: keep the token in memory only */
  }
}

async function call(path, { token, method = "GET", body } = {}) {
  let resp;
  try {
    resp = await fetch(`/api/admin${path}`, {
      method,
      body,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    throw { status: "network_error", message: "Couldn't reach PolicyPal. Check your connection and retry." };
  }
  let data = null;
  try {
    data = await resp.json();
  } catch {
    data = null;
  }
  if (!resp.ok) {
    throw {
      status: data?.status || "error",
      message: data?.message || `The server returned HTTP ${resp.status}.`,
      httpStatus: resp.status,
    };
  }
  return data;
}

export const adminStatus = () => call("/status");
export const listPolicies = (token) => call("/policies", { token });
export const removePolicy = (token, id) => call(`/policies/${encodeURIComponent(id)}`, { token, method: "DELETE" });
export const resetPolicies = (token) => call("/reset", { token, method: "POST" });
export const reindexPolicies = (token) => call("/reindex", { token, method: "POST" });

export function uploadPolicy(token, file, fields) {
  const body = new FormData();
  body.append("file", file);
  for (const [k, v] of Object.entries(fields)) if (v && String(v).trim()) body.append(k, String(v).trim());
  return call("/policies", { token, method: "POST", body });
}
