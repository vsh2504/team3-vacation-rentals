// Frontend — Shared, no single owner (like backend routers/common.py).
// The only place the frontend touches HTTP; every page imports from here.
//
// Patterns:
//   Factory   createApi(baseUrl, fetchImpl) builds an independent client.
//   Singleton `api` is the one shared client every page imports.
//   Facade    `api.*` hides URLs, verbs, headers and error handling behind
//             one method per use-case.
//   Decorator jsonBody() / bearer() wrap request options without mutating them.
//   Adapter   normalizeError() turns any backend error payload into text.
//
// Base URL: /api in dev (Vite proxy), or VITE_API_URL in production.
// Auth: the token is held by the auth store and passed explicitly here, so no
// page ever invents its own fetch logic.
const BASE = import.meta.env.VITE_API_URL || '/api';

// Adapter: string, FastAPI 422 array, {message}, {error:{message}} -> readable text.
export function normalizeError(body) {
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

// Builds "?a=1&b=2", dropping empty values.
export const qs = (q = {}) => {
  const e = Object.entries(q).filter(([, v]) => v !== '' && v != null);
  return e.length ? `?${new URLSearchParams(e)}` : '';
};

// Decorators over fetch options.
export const jsonBody = (payload) => (opts) => ({ ...opts, body: JSON.stringify(payload) });
export const bearer = (token) => (opts) => ({
  ...opts, headers: { ...(opts.headers || {}), Authorization: `Bearer ${token}` } });
const decorate = (opts, ...decorators) => decorators.reduce((o, wrap) => wrap(o), opts);

export function createApi(baseUrl = BASE, fetchImpl = (...args) => globalThis.fetch(...args)) {
  async function req(path, opts = {}) {
    const res = await fetchImpl(`${baseUrl}${path}`, {
      ...opts, headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) } });
    const body = await res.json().catch(() => null);
    // PR 15 fix: any non-OK status, any success:false, and any missing data
    // all throw, so callers fall back (search -> seed) instead of crashing.
    if (!res.ok) throw new Error(normalizeError(body) || `Request failed: ${path} (${res.status})`);
    if (!body || body.success === false) {
      throw new Error(normalizeError(body) || `Request failed: ${path} (${res.status})`);
    }
    if (body.data === undefined) throw new Error(`Request failed: ${path} — no data in response`);
    return body.data;
  }

  // Uploads a File/Blob as the raw request body; returns {url, kind}. The url is
  // prefixed with the base so <img src> resolves through the dev proxy or VITE_API_URL.
  async function uploadMedia(token, file) {
    const res = await fetchImpl(`${baseUrl}/uploads`, decorate(
      { method: 'POST', headers: { 'Content-Type': file.type }, body: file }, bearer(token)));
    const body = await res.json().catch(() => null);
    if (!res.ok || !body || body.success === false) {
      throw new Error(normalizeError(body) || `Upload failed (${res.status})`);
    }
    return { ...body.data, url: `${baseUrl}${body.data.url}` };
  }

  const authed = (t, opts = {}, ...more) => decorate(opts, bearer(t), ...more);

  return {
    uploadMedia,
    health: () => req('/health'),
    // Auth / admin (Ranadhir)
    register: (b) => req('/auth/register', decorate({ method: 'POST' }, jsonBody(b))),
    login: (b) => req('/auth/login', decorate({ method: 'POST' }, jsonBody(b))),
    me: (t) => req('/auth/me', authed(t)),
    adminListings: (t, status) => req(`/admin/listings${status ? `?status=${status}` : ''}`, authed(t)),
    approve: (t, id) => req(`/admin/listings/${id}/approve`, authed(t, { method: 'POST' })),
    reject: (t, id) => req(`/admin/listings/${id}/reject`, authed(t, { method: 'POST' })),
    adminRemove: (t, id) => req(`/admin/listings/${id}`, authed(t, { method: 'DELETE' })),
    // Search / listings (Vinayak)
    search: (q) => req(`/listings/search${qs(q)}`),
    listing: (id, q = {}) => req(`/listings/${id}${qs(q)}`),
    listingAvailability: (id, q = {}) => req(`/listings/${id}/availability${qs(q)}`),
    geocode: (address) => req(`/geocode?${new URLSearchParams({ address })}`),
    hostListings: (t) => req('/host/listings', authed(t)),
    createListing: (t, b) => req('/listings', authed(t, { method: 'POST' }, jsonBody(b))),
    updateListing: (t, id, b) => req(`/listings/${id}`, authed(t, { method: 'PUT' }, jsonBody(b))),
    deleteListing: (t, id) => req(`/listings/${id}`, authed(t, { method: 'DELETE' })),
    // Bookings (Manoj)
    book: (t, b) => req('/bookings', authed(t, { method: 'POST' }, jsonBody(b))),
    hostBookings: (t) => req('/host/bookings', authed(t)),
    myBookings: (t) => req('/bookings/me', authed(t)),
    cancelBooking: (t, id) => req(`/bookings/${id}/cancel`, authed(t, { method: 'POST' })),
    completeBooking: (t, id) => req(`/bookings/${id}/complete`, authed(t, { method: 'POST' })),
    // Reviews / analytics (Prajval)
    review: (t, b) => req('/reviews', authed(t, { method: 'POST' }, jsonBody(b))),
    listingReviews: (id) => req(`/listings/${id}/reviews`),
    hostAnalytics: (t, days, zip) => req(`/host/analytics?days=${days}${zip ? `&zip=${zip}` : ''}`, authed(t)),
    adminAnalytics: (t, days, zip) => req(`/admin/analytics?days=${days}${zip ? `&zip=${zip}` : ''}`, authed(t)),
  };
}

export const api = createApi();
