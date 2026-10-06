import { config } from "../config.js";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, timeoutMs = 12000 } = {}) {
  const res = await fetch(`${config.RCA_API_URL}${path}`, {
    method,
    credentials: "same-origin",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });

  let payload = null;
  try {
    payload = await res.json();
  } catch {
    payload = null;
  }

  if (!res.ok) {
    throw new ApiError(res.status, payload?.detail || `HTTP ${res.status}`);
  }
  return payload;
}

export const authApi = {
  me: () => request("/auth/me"),
  login: (username, password) => request("/auth/login", { method: "POST", body: { username, password } }),
  logout: () => request("/auth/logout", { method: "POST" }),
};

export const adminApi = {
  listUsers: () => request("/users"),
  createUser: (username, password, role) =>
    request("/users", { method: "POST", body: { username, password, role } }),
  setRole: (username, role) =>
    request(`/users/${encodeURIComponent(username)}/role`, { method: "PATCH", body: { role } }),
  trigger: (scenario) =>
    request("/trigger", { method: "POST", body: { scenario }, timeoutMs: 25000 }),
};

export const incidentApi = {
  acknowledge: (traceId) =>
    request(`/incidents/${encodeURIComponent(traceId)}/acknowledge`, { method: "POST" }),
};
