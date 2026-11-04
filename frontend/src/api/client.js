// One typed API client — the only place the frontend touches HTTP.
// Base URL: /api in dev (Vite proxy), or VITE_API_URL in production.
const BASE = import.meta.env.VITE_API_URL || '/api';
async function req(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) }, ...opts });
  const body = await res.json().catch(() => null);
  if (!body || body.success === false) throw new Error(body?.error?.message || `Request failed: ${path}`);
  return body.data;
}
export const api = {
  health: () => req('/health'),
  search: (q) => req(`/listings/search?${new URLSearchParams(q)}`),
  listing: (id) => req(`/listings/${id}`),
  book: (payload, token) => req('/bookings', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) }),
};
