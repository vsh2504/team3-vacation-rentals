import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import RoleGuard from './RoleGuard.jsx';

const view = (auth) => render(
  <RoleGuard auth={auth} roles={['ADMIN']} loggedOut={<p>log in</p>} denied={<p>denied</p>}>
    <p>secret</p>
  </RoleGuard>);

describe('RoleGuard (Protection Proxy)', () => {
  it('shows the logged-out message without a session', () => {
    view(null);
    expect(screen.getByText('log in')).toBeInTheDocument();
  });
  it('denies a session whose role is not allowed', () => {
    view({ user: { role: 'HOST' } });
    expect(screen.getByText('denied')).toBeInTheDocument();
    expect(screen.queryByText('secret')).toBeNull();
  });
  it('denies a session with no user', () => {
    view({});
    expect(screen.getByText('denied')).toBeInTheDocument();
  });
  it('renders the protected content for an allowed role', () => {
    view({ user: { role: 'ADMIN' } });
    expect(screen.getByText('secret')).toBeInTheDocument();
  });
});
