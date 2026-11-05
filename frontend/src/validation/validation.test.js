import { describe, expect, it } from 'vitest';
import { Rule, chain } from './chain.js';
import { nightsBetween, validateSearch } from './search.js';
import { validateAuth } from './auth.js';
import { bookingProblem, stayNights } from './booking.js';

describe('Rule / chain (Chain of Responsibility)', () => {
  it('runs every handler in order and collects errors', () => {
    const order = [];
    const head = chain(
      new Rule((c, e) => { order.push(1); e.a = 'first'; }),
      new Rule((c, e) => { order.push(2); e.b = 'second'; }),
      new Rule(() => { order.push(3); }));
    expect(head.run({})).toEqual({ a: 'first', b: 'second' });
    expect(order).toEqual([1, 2, 3]);
  });
  it('can stop at the first failure', () => {
    const seen = [];
    const head = chain(new Rule((c, e) => { seen.push(1); e.a = 'x'; }), new Rule(() => seen.push(2)));
    expect(head.run({}, {}, true)).toEqual({ a: 'x' });
    expect(seen).toEqual([1]);
  });
  it('continues past passing handlers when stopping on first failure', () => {
    const head = chain(new Rule(() => {}), new Rule((c, e) => { e.z = 'late'; }));
    expect(head.run({}, {}, true)).toEqual({ z: 'late' });
  });
  it('a single rule is a valid chain', () => {
    expect(chain(new Rule((c, e) => { e.only = 1; })).run({})).toEqual({ only: 1 });
  });
});

describe('validateSearch', () => {
  const ok = { guests: 2, checkIn: '', checkOut: '' };
  it('accepts a minimal valid search', () => expect(validateSearch(ok)).toEqual({}));
  it('requires at least one guest', () => {
    expect(validateSearch({ ...ok, guests: 0 }).guests).toBe('Enter at least 1 guest.');
    expect(validateSearch({ ...ok, guests: '' }).guests).toBe('Enter at least 1 guest.');
  });
  it('requires both dates together', () => {
    expect(validateSearch({ ...ok, checkIn: '2027-05-01' }).checkOut).toBe('Choose a check-out date.');
    expect(validateSearch({ ...ok, checkOut: '2027-05-03' }).checkIn).toBe('Choose a check-in date.');
  });
  it('enforces ordering and the 14-night limit', () => {
    expect(validateSearch({ ...ok, checkIn: '2027-05-03', checkOut: '2027-05-01' }).checkOut)
      .toBe('Check-out must be after check-in.');
    expect(validateSearch({ ...ok, checkIn: '2027-05-01', checkOut: '2027-05-16' }).checkOut)
      .toBe('Stays are limited to 14 nights (you chose 15).');
    expect(validateSearch({ ...ok, checkIn: '2027-05-01', checkOut: '2027-05-15' })).toEqual({});
  });
  it('computes nights between dates', () => expect(nightsBetween('2027-05-01', '2027-05-04')).toBe(3));
});

describe('validateAuth', () => {
  const login = { mode: 'login', email: 'a@b.co', password: 'password1', fullName: '', role: 'CUSTOMER' };
  it('accepts valid login and register input', () => {
    expect(validateAuth(login)).toEqual({});
    expect(validateAuth({ ...login, mode: 'register', fullName: 'Al', role: 'HOST' })).toEqual({});
  });
  it('validates email', () => {
    expect(validateAuth({ ...login, email: '  ' }).email).toBe('Email address is required.');
    expect(validateAuth({ ...login, email: 'nope' }).email).toBe('Please enter a valid email address.');
  });
  it('validates password', () => {
    expect(validateAuth({ ...login, password: '' }).password).toBe('Password is required.');
    expect(validateAuth({ ...login, password: 'short' }).password).toBe('Password must be at least 8 characters.');
  });
  it('validates name and role only when registering', () => {
    expect(validateAuth({ ...login, fullName: '', role: 'BOGUS' })).toEqual({});
    const reg = validateAuth({ ...login, mode: 'register', fullName: ' ', role: 'BOGUS' });
    expect(reg.fullName).toBe('Full name is required.');
    expect(reg.role).toBe('Please select a valid account role.');
  });
});

describe('booking rules', () => {
  const customer = { token: 't', user: { role: 'CUSTOMER' } };
  it('computes stay nights', () => {
    expect(stayNights('2027-05-01', '2027-05-04')).toBe(3);
    expect(stayNights('', '2027-05-04')).toBe(0);
    expect(stayNights('2027-05-01', '')).toBe(0);
  });
  it('requires a signed-in customer', () => {
    expect(bookingProblem({ auth: null })).toBe('Please log in as a Customer to book this stay.');
    expect(bookingProblem({ auth: { user: { role: 'HOST' } } }))
      .toBe('Signed in as HOST. Only customer accounts can book stays. Please switch to a customer account.');
    expect(bookingProblem({ auth: { user: {} } })).toMatch(/^Signed in as user\./);
    expect(bookingProblem({ auth: { } })).toMatch(/^Signed in as user\./);
  });
  it('rejects backwards and over-long ranges, in that order of precedence', () => {
    expect(bookingProblem({ auth: customer, checkIn: '2027-05-04', checkOut: '2027-05-01' }))
      .toBe('Check-out date must be strictly after check-in date.');
    expect(bookingProblem({ auth: customer, checkIn: '2027-05-01', checkOut: '2027-05-20' }))
      .toBe('Stays cannot exceed 14 nights (StayNest policy). Please select a shorter duration.');
  });
  it('accepts a valid request', () => {
    expect(bookingProblem({ auth: customer, checkIn: '2027-05-01', checkOut: '2027-05-04' })).toBeNull();
    expect(bookingProblem({ auth: customer, checkIn: '', checkOut: '' })).toBeNull();
  });
});
