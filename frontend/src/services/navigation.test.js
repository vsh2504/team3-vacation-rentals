import { describe, expect, it } from 'vitest';
import { homePathFor, isActive, navLinksFor, roleBadgeVariant } from './navigation.js';

const keys = (role) => navLinksFor(role).map(l => l.to);

describe('navigation strategies', () => {
  it('guests only see search', () => {
    expect(keys(null)).toEqual(['/']);
    expect(keys(undefined)).toEqual(['/']);
  });
  it('customers (and unknown signed-in roles) see search and bookings', () => {
    expect(keys('CUSTOMER')).toEqual(['/', '/bookings']);
    expect(keys('SOMETHING')).toEqual(['/', '/bookings']);
  });
  it('hosts see their listings, bookings & reviews and analytics', () => {
    expect(navLinksFor('HOST').map(l => l.label)).toEqual(
      ['My listings', 'Bookings & reviews', 'Analytics']);
  });
  it('admins see the approvals queue and analytics', () => {
    expect(navLinksFor('ADMIN').map(l => l.label)).toEqual(['Approvals queue', 'Analytics']);
  });
  it('returns fresh arrays so callers cannot mutate a strategy', () => {
    navLinksFor('HOST').pop();
    expect(navLinksFor('HOST')).toHaveLength(3);
  });
});

describe('homePathFor / roleBadgeVariant', () => {
  it.each([['HOST', '/host'], ['ADMIN', '/admin'], ['CUSTOMER', '/'], [undefined, '/']])(
    '%s -> %s', (role, path) => expect(homePathFor(role)).toBe(path));
  it.each([['ADMIN', 'accent'], ['HOST', 'primary'], ['CUSTOMER', 'neutral'], [undefined, 'neutral']])(
    '%s badge -> %s', (role, variant) => expect(roleBadgeVariant(role)).toBe(variant));
});

describe('isActive', () => {
  it('matches exactly or by prefix', () => {
    expect(isActive({ to: '/host', match: 'exact' }, '/host')).toBe(true);
    expect(isActive({ to: '/host', match: 'exact' }, '/host/bookings')).toBe(false);
    expect(isActive({ to: '/bookings', match: 'prefix' }, '/bookings/4')).toBe(true);
    expect(isActive({ to: '/bookings', match: 'prefix' }, '/')).toBe(false);
  });
});
