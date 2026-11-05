// Frontend — Owner: Ranadhir Reddy Rikkala (platform / routing)
// Feature: Identity, Platform & Admin Control — app shell, role nav, auth state.
// Pages themselves are owned by their feature owners (see their headers).
import React, { useEffect, useState } from 'react';
import { Link, Route, Routes, useNavigate } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import SearchPage from './pages/SearchPage.jsx';
import ListingDetailPage from './pages/ListingDetailPage.jsx';
import AuthPage from './pages/AuthPage.jsx';
import HostPage from './pages/HostPage.jsx';
import BookingsPage from './pages/BookingsPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import AnalyticsPage from './pages/AnalyticsPage.jsx';
// Sprint 1-4 app: real auth state (token + user in localStorage), role nav.
// The API still enforces every rule — hiding a nav link is UX, not security.
export default function App() {
  const [auth, setAuth] = useState(() => {
    try { return JSON.parse(localStorage.getItem('staynest_auth') || 'null'); } catch { return null; }
  });
  const navigate = useNavigate();
  function onAuth(token, user) {
    const a = { token, user };
    setAuth(a); localStorage.setItem('staynest_auth', JSON.stringify(a)); navigate('/');
  }
  function logout() {
    setAuth(null); localStorage.removeItem('staynest_auth'); navigate('/');
  }
  const role = auth?.user?.role;
  return (
    <div className="app">
      <header className="site-header"><h1 className="logo">StayNest</h1>
        <nav className="site-nav">
          <Link to="/">Search</Link>{' | '}
          {role === 'HOST' && <><Link to="/host">My listings</Link>{' | '}</>}
          {auth && <><Link to="/bookings">My bookings</Link>{' | '}</>}
          {role === 'ADMIN' && <><Link to="/admin">Admin</Link>{' | '}</>}
          {(role === 'HOST' || role === 'ADMIN') && <><Link to="/analytics">Analytics</Link>{' | '}</>}
          {auth ? <><span>Signed in as {auth.user.email} ({role})</span>{' '}<button onClick={logout}>Log out</button></>
            : <Link to="/auth">Log in / Register</Link>}
        </nav>
      </header>
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
      <footer><p><small>StayNest (Team 3) — API: /docs on the backend. If the API is not running, search falls back to seed data.</small></p></footer>
    </div>
  );
}
