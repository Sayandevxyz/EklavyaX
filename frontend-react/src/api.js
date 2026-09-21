const API_BASE = import.meta.env.VITE_API_BASE || "";
const TOKEN_KEY = "EklavyaX_token";
const USER_KEY = "EklavyaX_user";

export function getSession() {
  const token = localStorage.getItem(TOKEN_KEY);
  const rawUser = localStorage.getItem(USER_KEY);
  return { token, user: rawUser ? JSON.parse(rawUser) : null };
}

export function saveSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function request(path, options = {}) {
  const { token } = getSession();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error("Could not reach the EklavyaX server. Start the FastAPI backend on port 8000.");
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail || data?.message || `Request failed (${response.status})`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export function login(username, password) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
}

export function register(payload) {
  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getProfile() {
  return request("/auth/me");
}

export function getWallet() {
  return request("/economy/wallet");
}

export function getLeaderboard() {
  return request("/leaderboard/class");
}
