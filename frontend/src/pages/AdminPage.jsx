// Frontend — Owner: Ranadhir Reddy Rikkala
// Feature: Identity, Platform & Admin Control — approvals queue + moderation.
import React, { useEffect, useState } from 'react';
import { api } from '../api/client.js';
// Sprint 2 (Ranadhir): approvals queue + moderation. API enforces ADMIN only.
export default function AdminPage({ auth }) {
  const [pending, setPending] = useState([]); const [all, setAll] = useState([]); const [msg, setMsg] = useState(''); const [error, setError] = useState('');
  function load() {
    if (!auth) return;
    api.adminListings(auth.token, 'PENDING_APPROVAL').then(setPending).catch(e => setError(e.message));
    api.adminListings(auth.token).then(setAll).catch(() => {});
  }
  useEffect(load, [auth]);
  if (!auth) return <p>Log in as Admin.</p>;
  if (auth.user.role !== 'ADMIN') return <p>Admin page — only ADMIN accounts (API enforces 403).</p>;
  async function act(fn, id, okMsg) { try { await fn(auth.token, id); setMsg(okMsg); load(); } catch (err) { setError(err.message); } }
  return (
    <section>
      <h2>Admin — approvals queue</h2>
      {pending.length === 0 && <p>No pending listings.</p>}
      {pending.map(l => <article className="page-card">
        <strong>{l.title}</strong> — {l.city} {l.zip} — ${l.price_per_night}/night — host #{l.host_id}{' '}
        <button onClick={() => act(api.approve, l.id, `Listing #${l.id} approved — it now appears in search.`)}>Approve</button>{' '}
        <button onClick={() => act(api.reject, l.id, `Listing #${l.id} rejected.`)}>Reject</button>
      </article>)}
      <h3>All listings ({all.length})</h3>
      {all.map(l => <article className="page-card">
        #{l.id} {l.title} — {l.status}{' '}
        {l.status !== 'REMOVED' && <button onClick={() => act(api.adminRemove, l.id, `Listing #${l.id} removed.`)}>Remove</button>}
      </article>)}
      {msg && <p>{msg}</p>}{error && <p role="alert">{error}</p>}
    </section>
  );
}
