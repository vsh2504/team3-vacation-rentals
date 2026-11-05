import { describe, expect, it, vi } from 'vitest';
import { api, bearer, createApi, jsonBody, normalizeError, qs } from './client.js';

const ok = (data, status = 200) => ({ ok: status < 400, status, json: async () => ({ success: true, data }) });
const make = (response) => {
  const fetchImpl = vi.fn().mockResolvedValue(response);
  return { fetchImpl, client: createApi('/base', fetchImpl) };
};

describe('normalizeError (Adapter)', () => {
  it.each([
    [{ error: 'plain' }, 'plain'],
    [{ detail: 'Not Found' }, 'Not Found'],
    [{ message: 'top' }, 'top'],
    [{ error: { message: 'nested' } }, 'nested'],
    [{ detail: [{ loc: ['body', 'email'], msg: 'bad' }, { msg: 'other' }] }, 'email: bad; other'],
    [{ detail: [null, 'x'] }, 'x'],
    [{ error: { detail: 5 } }, '5'],
    [{ error: { error: 'deep' } }, 'deep'],
    [{ error: { loc: ['body'], msg: '' } }, ''],
    [{ error: { loc: ['email'], msg: '' } }, ''],
    [{ error: { loc: 'nope', msg: 'm' } }, 'm'],
    [null, ''], [undefined, ''], [{}, ''],
  ])('%j -> %j', (body, expected) => expect(normalizeError(body)).toBe(expected));
});

describe('qs', () => {
  it('drops empty values and builds a query string', () => {
    expect(qs({ a: 1, b: '', c: null, d: undefined, e: 'x y' })).toBe('?a=1&e=x+y');
    expect(qs({})).toBe('');
    expect(qs()).toBe('');
  });
});

describe('request decorators', () => {
  it('jsonBody and bearer wrap options without mutating them', () => {
    const base = { method: 'POST' };
    expect(jsonBody({ a: 1 })(base)).toEqual({ method: 'POST', body: '{"a":1}' });
    expect(bearer('t')({ headers: { X: '1' } })).toEqual({ headers: { X: '1', Authorization: 'Bearer t' } });
    expect(bearer('t')({}).headers.Authorization).toBe('Bearer t');
    expect(base).toEqual({ method: 'POST' });
  });
});

describe('createApi (Factory) / req', () => {
  it('returns data and sends JSON content type to the base url', async () => {
    const { fetchImpl, client } = make(ok({ status: 'ok' }));
    expect(await client.health()).toEqual({ status: 'ok' });
    expect(fetchImpl).toHaveBeenCalledWith('/base/health', {
      headers: { 'Content-Type': 'application/json' } });
  });

  it('throws the normalized message for non-OK responses', async () => {
    const { client } = make({ ok: false, status: 404, json: async () => ({ detail: 'Not Found' }) });
    await expect(client.health()).rejects.toThrow('Not Found');
  });

  it('falls back to a status message when the body is unreadable', async () => {
    const { client } = make({ ok: false, status: 500, json: async () => { throw new Error('x'); } });
    await expect(client.health()).rejects.toThrow('Request failed: /health (500)');
  });

  it('throws on success:false, missing body and missing data', async () => {
    await expect(make({ ok: true, status: 200, json: async () => ({ success: false, error: { message: 'no' } }) })
      .client.health()).rejects.toThrow('no');
    await expect(make({ ok: true, status: 200, json: async () => null }).client.health())
      .rejects.toThrow('Request failed: /health (200)');
    await expect(make({ ok: true, status: 200, json: async () => ({ success: true }) }).client.health())
      .rejects.toThrow('no data in response');
  });
});

describe('endpoint facade', () => {
  const cases = [
    ['register', [{ a: 1 }], '/base/auth/register', 'POST', '{"a":1}', false],
    ['login', [{ a: 1 }], '/base/auth/login', 'POST', '{"a":1}', false],
    ['me', ['T'], '/base/auth/me', undefined, undefined, true],
    ['adminListings', ['T', 'APPROVED'], '/base/admin/listings?status=APPROVED', undefined, undefined, true],
    ['adminListings', ['T'], '/base/admin/listings', undefined, undefined, true],
    ['approve', ['T', 4], '/base/admin/listings/4/approve', 'POST', undefined, true],
    ['reject', ['T', 4], '/base/admin/listings/4/reject', 'POST', undefined, true],
    ['adminRemove', ['T', 4], '/base/admin/listings/4', 'DELETE', undefined, true],
    ['search', [{ city: 'SJ' }], '/base/listings/search?city=SJ', undefined, undefined, false],
    ['listing', [3, { guests: 2 }], '/base/listings/3?guests=2', undefined, undefined, false],
    ['listing', [3], '/base/listings/3', undefined, undefined, false],
    ['listingAvailability', [3, { guests: 2 }], '/base/listings/3/availability?guests=2', undefined, undefined, false],
    ['listingAvailability', [3], '/base/listings/3/availability', undefined, undefined, false],
    ['geocode', ['1 Main St'], '/base/geocode?address=1+Main+St', undefined, undefined, false],
    ['hostListings', ['T'], '/base/host/listings', undefined, undefined, true],
    ['createListing', ['T', { t: 1 }], '/base/listings', 'POST', '{"t":1}', true],
    ['updateListing', ['T', 3, { t: 1 }], '/base/listings/3', 'PUT', '{"t":1}', true],
    ['deleteListing', ['T', 3], '/base/listings/3', 'DELETE', undefined, true],
    ['book', ['T', { l: 1 }], '/base/bookings', 'POST', '{"l":1}', true],
    ['hostBookings', ['T'], '/base/host/bookings', undefined, undefined, true],
    ['myBookings', ['T'], '/base/bookings/me', undefined, undefined, true],
    ['cancelBooking', ['T', 9], '/base/bookings/9/cancel', 'POST', undefined, true],
    ['completeBooking', ['T', 9], '/base/bookings/9/complete', 'POST', undefined, true],
    ['review', ['T', { r: 5 }], '/base/reviews', 'POST', '{"r":5}', true],
    ['listingReviews', [3], '/base/listings/3/reviews', undefined, undefined, false],
    ['hostAnalytics', ['T', 30, '95110'], '/base/host/analytics?days=30&zip=95110', undefined, undefined, true],
    ['hostAnalytics', ['T', 30], '/base/host/analytics?days=30', undefined, undefined, true],
    ['adminAnalytics', ['T', 60, '95110'], '/base/admin/analytics?days=60&zip=95110', undefined, undefined, true],
    ['adminAnalytics', ['T', 60], '/base/admin/analytics?days=60', undefined, undefined, true],
  ];
  it.each(cases)('%s(%j) -> %s', async (name, args, url, method, body, authed) => {
    const { fetchImpl, client } = make(ok({ done: true }));
    expect(await client[name](...args)).toEqual({ done: true });
    const [calledUrl, opts] = fetchImpl.mock.calls[0];
    expect(calledUrl).toBe(url);
    expect(opts.method).toBe(method);
    expect(opts.body).toBe(body);
    expect(opts.headers.Authorization).toBe(authed ? 'Bearer T' : undefined);
  });
});

describe('uploadMedia', () => {
  const file = { type: 'image/png' };
  it('posts the raw file and prefixes the returned url with the base', async () => {
    const { fetchImpl, client } = make(ok({ url: '/uploads/a.png', kind: 'photo' }));
    expect(await client.uploadMedia('T', file)).toEqual({ url: '/base/uploads/a.png', kind: 'photo' });
    expect(fetchImpl).toHaveBeenCalledWith('/base/uploads', {
      method: 'POST', headers: { Authorization: 'Bearer T', 'Content-Type': 'image/png' }, body: file });
  });
  it('throws a readable error on failure', async () => {
    const bad = make({ ok: false, status: 422, json: async () => ({ error: { message: 'too big' } }) });
    await expect(bad.client.uploadMedia('T', file)).rejects.toThrow('too big');
    const unreadable = make({ ok: false, status: 500, json: async () => { throw new Error('x'); } });
    await expect(unreadable.client.uploadMedia('T', file)).rejects.toThrow('Upload failed (500)');
    const missing = make({ ok: true, status: 200, json: async () => null });
    await expect(missing.client.uploadMedia('T', file)).rejects.toThrow('Upload failed (200)');
  });
});

describe('default singleton', () => {
  it('is one shared facade bound to global fetch', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(ok({ ping: 1 }));
    expect(await api.health()).toEqual({ ping: 1 });
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/health', expect.any(Object));
    expect(api).toBe((await import('./client.js')).api);
  });
});
