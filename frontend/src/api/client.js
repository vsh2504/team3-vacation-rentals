// Frontend — Shared, no single owner (like backend routers/common.py).
// The only place the frontend touches HTTP; every page imports from here.
// One typed API client — the only place the frontend touches HTTP.
// Base URL: /api in dev (Vite proxy), or VITE_API_URL in production.
// Auth: token is stored in localStorage by App.jsx and passed explicitly
// here, so no page ever invents its own fetch logic.
const BASE = import.meta.env.VITE_API_URL || '/api';
// Turns any error payload (string, FastAPI 422 array, {message}, {error:{message}}) into readable text.
function errText(body) {
  const pick = v => {
    if (v == null) return '';
    if (typeof v === 'string') return v;
    if (Array.isArray(v)) return v.map(pick).filter(Boolean).join('; ');
    if (typeof v === 'object') {
      const m = pick(v.message ?? v.msg ?? v.detail ?? v.error);
      const loc = Array.isArray(v.loc) ? v.loc.filter(x => x !== 'body').join('.') : '';
      return loc && m ? `${loc}: ${m}` : m;
    }
    return String(v);
  };
  return pick(body?.error) || pick(body?.detail) || pick(body?.message);
}
async function req(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, { ...opts, headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) } });
  const body = await res.json().catch(() => null);
  // PR 15 fix: previously only body.success === false threw. A FastAPI
  // 404 body {"detail": "Not Found"} has no success field, so it fell
  // through and returned body.data === undefined, which crashed
  // SearchPage on results.length. Now any non-OK status, any
  // success:false, and any missing data all throw, so callers fall
  // back (search -> seed) instead of crashing.
  if (!res.ok) throw new Error(errText(body) || `Request failed: ${path} (${res.status})`);
  if (!body || body.success === false) throw new Error(errText(body) || `Request failed: ${path} (${res.status})`);
  if (body.data === undefined) throw new Error(`Request failed: ${path} — no data in response`);
  return body.data;
}
// Builds "?a=1&b=2", dropping empty values.
export const qs = (q = {}) => {
  const e = Object.entries(q).filter(([, v]) => v !== '' && v != null);
  return e.length ? `?${new URLSearchParams(e)}` : '';
};
const authH = (token) => ({ Authorization: `Bearer ${token}` });
// Uploads a File/Blob as the raw request body; returns {url, kind}. The url is
// prefixed with BASE so <img src> resolves through the dev proxy or VITE_API_URL.
async function uploadMedia(token, file) {
  const res = await fetch(`${BASE}/uploads`, { method: 'POST', headers: { ...authH(token), 'Content-Type': file.type }, body: file });
  const body = await res.json().catch(() => null);
  if (!res.ok || !body || body.success === false) throw new Error(errText(body) || `Upload failed (${res.status})`);
  return { ...body.data, url: `${BASE}${body.data.url}` };
}
export const api = {
  uploadMedia,
  health: () => req('/health'),
  // Auth / admin (Ranadhir)
  register: (b) => req('/auth/register', { method: 'POST', body: JSON.stringify(b) }),
  login: (b) => req('/auth/login', { method: 'POST', body: JSON.stringify(b) }),
  me: (t) => req('/auth/me', { headers: authH(t) }),
  adminListings: (t, status) => req(`/admin/listings${status ? `?status=${status}` : ''}`, { headers: authH(t) }),
  approve: (t, id) => req(`/admin/listings/${id}/approve`, { method: 'POST', headers: authH(t) }),
  reject: (t, id) => req(`/admin/listings/${id}/reject`, { method: 'POST', headers: authH(t) }),
  adminRemove: (t, id) => req(`/admin/listings/${id}`, { method: 'DELETE', headers: authH(t) }),
  // Search / listings (Vinayak)
  search: (q) => req(`/listings/search${qs(q)}`),
  listing: (id, q = {}) => req(`/listings/${id}${qs(q)}`),
  listingAvailability: (id, q = {}) => req(`/listings/${id}/availability${qs(q)}`),
  geocode: (address) => req(`/geocode?${new URLSearchParams({ address })}`),
  hostListings: (t) => req('/host/listings', { headers: authH(t) }),
  createListing: (t, b) => req('/listings', { method: 'POST', headers: authH(t), body: JSON.stringify(b) }),
  updateListing: (t, id, b) => req(`/listings/${id}`, { method: 'PUT', headers: authH(t), body: JSON.stringify(b) }),
  deleteListing: (t, id) => req(`/listings/${id}`, { method: 'DELETE', headers: authH(t) }),
  // Bookings (Manoj)
  book: (t, b) => req('/bookings', { method: 'POST', headers: authH(t), body: JSON.stringify(b) }),
  hostBookings: (t) => req('/host/bookings', { headers: authH(t) }),
  myBookings: (t) => req('/bookings/me', { headers: authH(t) }),
  cancelBooking: (t, id) => req(`/bookings/${id}/cancel`, { method: 'POST', headers: authH(t) }),
  completeBooking: (t, id) => req(`/bookings/${id}/complete`, { method: 'POST', headers: authH(t) }),
  // Reviews / analytics (Prajval)
  review: (t, b) => req('/reviews', { method: 'POST', headers: authH(t), body: JSON.stringify(b) }),
  listingReviews: (id) => req(`/listings/${id}/reviews`),
  hostAnalytics: (t, days, zip) => req(`/host/analytics?days=${days}${zip ? `&zip=${zip}` : ''}`, { headers: authH(t) }),
  adminAnalytics: (t, days, zip) => req(`/admin/analytics?days=${days}${zip ? `&zip=${zip}` : ''}`, { headers: authH(t) }),
};
