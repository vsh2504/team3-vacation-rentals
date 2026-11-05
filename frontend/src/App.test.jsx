import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App.jsx';
import { authStore } from './state/authStore.js';

vi.mock('./pages/SearchPage.jsx', () => ({ default: () => <div>SearchPage</div> }));
vi.mock('./pages/ListingDetailPage.jsx', () => ({ default: () => <div>ListingDetailPage</div> }));
vi.mock('./pages/HostPage.jsx', () => ({ default: () => <div>HostPage</div> }));
vi.mock('./pages/BookingsPage.jsx', () => ({ default: () => <div>BookingsPage</div> }));
vi.mock('./pages/AdminPage.jsx', () => ({ default: () => <div>AdminPage</div> }));
vi.mock('./pages/AnalyticsPage.jsx', () => ({ default: () => <div>AnalyticsPage</div> }));
vi.mock('./pages/HostBookingsPage.jsx', () => ({ default: () => <div>HostBookingsPage</div> }));
vi.mock('./pages/AuthPage.jsx', () => ({
  default: ({ onAuth }) => (
    <div>
      AuthPage
      <button onClick={() => onAuth('tok', { email: 'h@x.io', role: 'HOST' })}>sign in host</button>
      <button onClick={() => onAuth('tok', { email: 'c@x.io', role: 'CUSTOMER' })}>sign in customer</button>
    </div>
  ),
}));

const Where = () => <output data-testid="where">{useLocation().pathname}</output>;
const view = (path = '/') => render(
  <MemoryRouter initialEntries={[path]}><App /><Where /></MemoryRouter>);
const as = (role, email = `${role}@x.io`) => act(() => authStore.login('tok', { email, role }));
const where = () => screen.getByTestId('where').textContent;
const navLabels = () => within_nav().map(a => a.textContent);
const within_nav = () => [...document.querySelectorAll('#primary-navigation a.nav-link')];

afterEach(() => act(() => authStore.logout()));

describe('guest', () => {
  it('sees search and the sign-in link only', () => {
    view('/');
    expect(screen.getByText('SearchPage')).toBeInTheDocument();
    expect(navLabels()).toEqual(['Search', 'Sign in / Register']);
    expect(document.querySelector('a.nav-link.is-active').textContent).toBe('Search');
  });

  it.each([
    ['/listings/3', 'ListingDetailPage'], ['/auth', 'AuthPage'], ['/host', 'HostPage'],
    ['/host/bookings', 'HostBookingsPage'], ['/bookings', 'BookingsPage'],
    ['/admin', 'AdminPage'], ['/analytics', 'AnalyticsPage'],
  ])('routes %s', (path, text) => {
    view(path);
    expect(screen.getByText(text)).toBeInTheDocument();
  });

  it('highlights the sign-in link on /auth', () => {
    view('/auth');
    expect(document.querySelector('a.nav-link.is-active').textContent).toBe('Sign in / Register');
  });

  it('has a skip link and landmarks', () => {
    view('/');
    expect(screen.getByText('Skip to main content')).toHaveAttribute('href', '#main-content');
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
    expect(screen.getByLabelText('StayNest Home')).toHaveAttribute('href', '/');
  });
});

describe('signed-in roles', () => {
  it('customers see bookings, their email and a role badge, and can log out', () => {
    as('CUSTOMER', 'c@x.io');
    view('/bookings');
    expect(screen.getByText('BookingsPage')).toBeInTheDocument();
    expect(navLabels()).toEqual(['Search', 'My bookings']);
    expect(screen.getByText('c@x.io')).toBeInTheDocument();
    expect(screen.getByText('CUSTOMER')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Log out of StayNest' }));
    expect(where()).toBe('/');
    expect(authStore.getState()).toBeNull();
    expect(screen.getByText('Sign in / Register')).toBeInTheDocument();
  });

  it('hosts are sent home to /host and see their own links', () => {
    as('HOST');
    view('/');
    expect(where()).toBe('/host');
    expect(navLabels()).toEqual(['My listings', 'Bookings & reviews', 'Analytics']);
    expect(screen.getByLabelText('StayNest Home')).toHaveAttribute('href', '/host');
    expect(screen.getByText('HOST')).toBeInTheDocument();
  });

  it('hosts cannot reach the customer bookings page', () => {
    as('HOST');
    view('/bookings');
    expect(where()).toBe('/host');
  });

  it('admins are sent to /admin and see the approvals queue', () => {
    as('ADMIN');
    view('/');
    expect(where()).toBe('/admin');
    expect(navLabels()).toEqual(['Approvals queue', 'Analytics']);
    expect(screen.getByText('AdminPage')).toBeInTheDocument();
  });

  it('highlights the active prefix link', () => {
    as('HOST');
    view('/host/bookings');
    expect(document.querySelector('a.nav-link.is-active').textContent).toBe('Bookings & reviews');
  });
});

describe('sign-in flow and mobile menu', () => {
  it('onAuth stores the session and navigates home', () => {
    view('/auth');
    fireEvent.click(screen.getByText('sign in host'));
    expect(authStore.getState().user.role).toBe('HOST');
    expect(where()).toBe('/host');
  });

  it('a customer signing in lands on search', () => {
    view('/auth');
    fireEvent.click(screen.getByText('sign in customer'));
    expect(where()).toBe('/');
    expect(screen.getByText('SearchPage')).toBeInTheDocument();
  });

  it('toggles the mobile menu and closes it on navigation', () => {
    view('/auth');
    const toggle = screen.getByLabelText('Toggle navigation menu');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(document.getElementById('primary-navigation')).toHaveClass('is-open');
    fireEvent.click(screen.getByText('Search'));
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(toggle);
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });
});
