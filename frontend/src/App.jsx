// Frontend — Owner: Ranadhir Reddy Rikkala (platform / routing)
// Feature: Identity, Platform & Admin Control — app shell, role nav, auth state.
// Polished application shell and shared UI system (Step 3.1).
import React, { useEffect, useState } from 'react';
import { Link, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import Badge from './components/ui/Badge.jsx';
import SearchPage from './pages/SearchPage.jsx';
import ListingDetailPage from './pages/ListingDetailPage.jsx';
import AuthPage from './pages/AuthPage.jsx';
import HostPage from './pages/HostPage.jsx';
import BookingsPage from './pages/BookingsPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import AnalyticsPage from './pages/AnalyticsPage.jsx';

export default function App() {
  const [auth, setAuth] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('staynest_auth') || 'null');
    } catch {
      return null;
    }
  });

  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // Close mobile navigation menu on route change
  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname]);

  function onAuth(token, user) {
    const a = { token, user };
    setAuth(a);
    localStorage.setItem('staynest_auth', JSON.stringify(a));
    navigate('/');
  }

  function logout() {
    setAuth(null);
    localStorage.removeItem('staynest_auth');
    navigate('/');
  }

  const role = auth?.user?.role;

  // Role badge variant helper
  function getRoleBadgeVariant(r) {
    if (r === 'ADMIN') return 'accent';
    if (r === 'HOST') return 'primary';
    return 'neutral';
  }

  return (
    <div className="app">
      {/* Accessible skip link for keyboard navigation (Requirement 8.4) */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <header className="site-header" role="banner">
        <div className="header-container">
          <div className="brand-wrapper">
            <Link to="/" className="logo-anchor" aria-label="StayNest Home">
              <span className="logo">StayNest</span>
            </Link>
            <span className="logo-badge" aria-hidden="true">Vacation Rentals</span>
          </div>

          {/* Mobile menu toggle (Requirement 8.2) */}
          <button
            type="button"
            className="nav-toggle"
            aria-expanded={isMenuOpen}
            aria-controls="primary-navigation"
            aria-label="Toggle navigation menu"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              {isMenuOpen ? (
                <>
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </>
              ) : (
                <>
                  <line x1="3" y1="12" x2="21" y2="12"></line>
                  <line x1="3" y1="6" x2="21" y2="6"></line>
                  <line x1="3" y1="18" x2="21" y2="18"></line>
                </>
              )}
            </svg>
          </button>

          {/* Navigation with role-appropriate exposure (Requirements 2.2, 2.4) */}
          <nav
            id="primary-navigation"
            className={`site-nav ${isMenuOpen ? 'is-open' : ''}`}
            role="navigation"
            aria-label="Main navigation"
          >
            <Link
              to="/"
              className={`nav-link ${location.pathname === '/' ? 'is-active' : ''}`}
            >
              Search
            </Link>

            {role === 'HOST' && (
              <Link
                to="/host"
                className={`nav-link ${location.pathname.startsWith('/host') ? 'is-active' : ''}`}
              >
                My listings
              </Link>
            )}

            {auth && (
              <Link
                to="/bookings"
                className={`nav-link ${location.pathname.startsWith('/bookings') ? 'is-active' : ''}`}
              >
                My bookings
              </Link>
            )}

            {role === 'ADMIN' && (
              <Link
                to="/admin"
                className={`nav-link ${location.pathname.startsWith('/admin') ? 'is-active' : ''}`}
              >
                Approvals queue
              </Link>
            )}

            {(role === 'HOST' || role === 'ADMIN') && (
              <Link
                to="/analytics"
                className={`nav-link ${location.pathname.startsWith('/analytics') ? 'is-active' : ''}`}
              >
                Analytics
              </Link>
            )}

            <span className="nav-divider" aria-hidden="true"></span>

            {/* User Session Bar */}
            <div className="user-session">
              {auth ? (
                <div className="user-info">
                  <span className="user-email" title={auth.user?.email}>
                    {auth.user?.email}
                  </span>
                  <Badge variant={getRoleBadgeVariant(role)}>
                    {role}
                  </Badge>
                  <button
                    type="button"
                    onClick={logout}
                    className="btn btn-secondary btn-sm"
                    aria-label="Log out of StayNest"
                  >
                    Log out
                  </button>
                </div>
              ) : (
                <Link
                  to="/auth"
                  className={`nav-link ${location.pathname === '/auth' ? 'is-active' : ''}`}
                >
                  Sign in / Register
                </Link>
              )}
            </div>
          </nav>
        </div>
      </header>

      {/* Main Content Landmark (Requirement 8.4) */}
      <main id="main-content" className="site-main" tabIndex="-1">
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/listings/:id" element={<ListingDetailPage auth={auth} />} />
            <Route path="/auth" element={<AuthPage onAuth={onAuth} />} />
            <Route path="/host" element={<HostPage auth={auth} />} />
            <Route path="/bookings" element={<BookingsPage auth={auth} />} />
            <Route path="/admin" element={<AdminPage auth={auth} />} />
            <Route path="/analytics" element={<AnalyticsPage auth={auth} />} />
          </Routes>
        </ErrorBoundary>
      </main>

      <footer className="site-footer" role="contentinfo">
        <p>
          <small>
            StayNest Vacation Rentals &bull; Harbor-town design system &bull;{' '}
            <a href="/docs" target="_blank" rel="noreferrer">Interactive API Docs (/docs)</a>
          </small>
        </p>
        <p>
          <small>
            API authorization remains the security boundary. Hiding routes is UX, not security.
          </small>
        </p>
      </footer>
    </div>
  );
}
