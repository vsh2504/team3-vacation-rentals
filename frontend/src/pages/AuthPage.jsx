// Frontend — Owner: Ranadhir Reddy Rikkala
// Feature: Identity, Platform & Admin Control — register/login page.
import React, { useState } from 'react';
import { api } from '../api/client.js';
// Sprint 1 (Ranadhir): register/login. Admin is seeded, not self-registered
// (API returns 403 for ADMIN role) — use admin@staynest.local / admin12345 in demo.
export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('CUSTOMER');
  const [error, setError] = useState('');
  async function submit(e) {
    e.preventDefault(); setError('');
    try {
      if (mode === 'register') await api.register({ email, password, full_name: fullName, role });
      const data = await api.login({ email, password });
      onAuth(data.access_token, data.user);
    } catch (err) { setError(err.message); }
  }
  return (
    <section>
      <h2>{mode === 'login' ? 'Log in' : 'Register'}</h2>
      <form onSubmit={submit}>
        {mode === 'register' && <><label>Full name <input required value={fullName} onChange={e => setFullName(e.target.value)} /></label><br />
          <label>Role <select value={role} onChange={e => setRole(e.target.value)}><option>CUSTOMER</option><option>HOST</option></select></label><br /></>}
        <label>Email <input required type="email" value={email} onChange={e => setEmail(e.target.value)} /></label><br />
        <label>Password <input required type="password" minLength={8} value={password} onChange={e => setPassword(e.target.value)} /></label><br />
        <button type="submit">{mode === 'login' ? 'Log in' : 'Register'}</button>{' '}
        <button type="button" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>Switch to {mode === 'login' ? 'register' : 'login'}</button>
      </form>
      {error && <p role="alert">{error}</p>}
      <p><small>Demo admin: admin@staynest.local / admin12345 (demo only, seeded on server startup).</small></p>
    </section>
  );
}
