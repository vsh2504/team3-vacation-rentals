import React, { useState } from 'react';
import SearchPage from './pages/SearchPage.jsx';
// Week 1 scaffold: role nav + search page only. Booking, host, and admin
// pages land in Sprints 1-2 behind the same api/client.js contract.
export default function App() {
  const [role, setRole] = useState('CUSTOMER');
  return (
    <div style={{ fontFamily: 'system-ui', maxWidth: 960, margin: '0 auto', padding: 16 }}>
      <header><h1>StayNest</h1>
        <nav>
          <button onClick={() => setRole('CUSTOMER')}>Customer</button>{' '}
          <button onClick={() => setRole('HOST')}>Host</button>{' '}
          <button onClick={() => setRole('ADMIN')}>Admin</button>
          <span> — viewing as {role} (Week 1: nav changes by role; API enforces it)</span>
        </nav>
      </header>
      <SearchPage role={role} />
      <p><small>Week 1: search UI calls the API contract in docs/contracts.md.
      If the API is not running, it falls back to local seed data so the
      wireframe can be demoed without a backend.</small></p>
    </div>
  );
}
