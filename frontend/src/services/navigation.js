// Pattern: Strategy. Each role supplies its own navigation policy and badge
// style; the shell asks the strategy instead of branching on role strings.
const link = (to, label, match = 'prefix') => ({ to, label, match });

const SEARCH = link('/', 'Search', 'exact');
const STRATEGIES = {
  GUEST: [SEARCH],
  CUSTOMER: [SEARCH, link('/bookings', 'My bookings')],
  HOST: [
    link('/host', 'My listings', 'exact'),
    link('/host/bookings', 'Bookings & reviews'),
    link('/analytics', 'Analytics'),
  ],
  ADMIN: [link('/admin', 'Approvals queue'), link('/analytics', 'Analytics')],
};

const strategyKey = (role) => (!role ? 'GUEST' : STRATEGIES[role] ? role : 'CUSTOMER');

export const navLinksFor = (role) => STRATEGIES[strategyKey(role)].map(item => ({ ...item }));

export const homePathFor = (role) => (role === 'HOST' ? '/host' : role === 'ADMIN' ? '/admin' : '/');

const BADGES = { ADMIN: 'accent', HOST: 'primary' };
export const roleBadgeVariant = (role) => BADGES[role] || 'neutral';

export const isActive = (item, pathname) =>
  (item.match === 'exact' ? pathname === item.to : pathname.startsWith(item.to));
