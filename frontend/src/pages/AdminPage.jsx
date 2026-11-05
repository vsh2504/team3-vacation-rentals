// Frontend — Owner: Ranadhir Reddy Rikkala
// Feature: Identity, Platform & Admin Control — moderation queue.
import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { Alert, Badge, Button, Card, Spinner, TableContainer } from '../components/ui/index.js';
import RoleGuard from '../components/RoleGuard.jsx';
import './dashboards.css';

const STATUS_VARIANT = { APPROVED: 'success', PENDING_APPROVAL: 'warning', REJECTED: 'danger', REMOVED: 'danger' };
const STATUS_LABEL = { APPROVED: 'Approved', PENDING_APPROVAL: 'Pending approval', REJECTED: 'Rejected', REMOVED: 'Removed' };
const FIELD_LABEL = { title: 'Title', description: 'Description', address: 'Address', city: 'City', state: 'State', zip: 'ZIP', coordinates: 'Map coordinates', price_per_night: 'Price', max_guests: 'Max guests', amenities: 'Amenities', available_times: 'Available times', operating_hours: 'Operating hours', contact: 'Contact info', media: 'Photos/videos' };
const label = k => FIELD_LABEL[k] || k;
const FILTERS = [['PENDING_APPROVAL', 'Pending'], ['', 'All listings'], ['APPROVED', 'Approved'], ['REJECTED', 'Rejected'], ['REMOVED', 'Removed']];

function StatusBadge({ status }) {
  return <Badge variant={STATUS_VARIANT[status] || 'neutral'}>{STATUS_LABEL[status] || status}</Badge>;
}

function ModerationCard({ l, busy, onAct }) {
  const c = l.completeness || { missing: [], score: 0, complete: false };
  const host = l.host;
  const first = l.photos?.[0];
  const addr = [l.address, l.city, [l.state, l.zip].filter(Boolean).join(' ')].filter(Boolean).join(', ');
  const titleId = `mod-${l.id}-title`;
  return (
    <Card as="article" aria-labelledby={titleId} className="mod-card">
      <div className="mod-top">
        <div>
          <h3 id={titleId} style={{ margin: 0 }}>{l.title || `Listing #${l.id}`}</h3>
          <p className="card-meta" style={{ margin: 0 }}>#{l.id} · ${l.price_per_night}/night · up to {l.max_guests} guests</p>
        </div>
        <div className="mod-actions">
          <StatusBadge status={l.status} />
          <Badge variant={c.complete ? 'success' : 'warning'}>{c.complete ? 'Complete' : `${c.score}% complete`}</Badge>
          <Badge variant={l.searchable ? 'primary' : 'neutral'}>{l.searchable ? 'Visible in search' : 'Hidden from search'}</Badge>
        </div>
      </div>
      <div className="mod-body">
        <div className="mod-media">
          {first ? <img src={first} alt={`${l.title} first photo`} loading="lazy" /> : <div className="empty" role="img" aria-label="No photo supplied">No photo</div>}
          <p className="card-meta">{l.photo_count ?? 0} photo(s), {l.video_count ?? 0} video(s)</p>
        </div>
        <dl className="mod-meta">
          <div><dt>Host</dt><dd>{host ? `${host.full_name} (${host.email})` : `Host #${l.host_id}`}{host?.phone ? ` · ${host.phone}` : ''}</dd></div>
          <div><dt>Address</dt><dd>{addr || '—'}</dd></div>
          <div><dt>Coordinates</dt><dd>{l.lat != null && l.lng != null ? `${l.lat}, ${l.lng}` : 'Missing'}</dd></div>
          <div><dt>Listing contact</dt><dd>{[l.host_contact_name, l.host_contact_email, l.host_contact_phone].filter(Boolean).join(' · ') || 'Missing'}</dd></div>
          <div><dt>Hours</dt><dd>{l.operating_start_time && l.operating_end_time ? `${l.operating_start_time}–${l.operating_end_time}` : '—'}{l.check_in_time ? ` · check-in ${l.check_in_time}` : ''}{l.check_out_time ? `, out ${l.check_out_time}` : ''}</dd></div>
          <div><dt>Amenities</dt><dd>{l.amenities?.length ? l.amenities.join(', ') : 'None'}</dd></div>
          <div style={{ gridColumn: '1 / -1' }}><dt>Description</dt><dd>{l.description || 'Missing'}</dd></div>
          <div style={{ gridColumn: '1 / -1' }}>
            <dt>Missing information</dt>
            <dd>{c.missing.length === 0 ? 'Nothing missing.' : <ul className="missing-list">{c.missing.map(m => <li key={m}><Badge variant="warning">{label(m)}</Badge></li>)}</ul>}</dd>
          </div>
        </dl>
      </div>
      <div className="mod-actions">
        {l.status !== 'APPROVED' && l.status !== 'REMOVED' && <Button isLoading={busy === `approve-${l.id}`} disabled={!!busy} onClick={() => onAct('approve', l, `"${l.title}" approved — it now appears in search.`)} aria-label={`Approve ${l.title}`}>Approve</Button>}
        {l.status === 'PENDING_APPROVAL' && <Button variant="secondary" isLoading={busy === `reject-${l.id}`} disabled={!!busy} onClick={() => onAct('reject', l, `"${l.title}" rejected.`)} aria-label={`Reject ${l.title}`}>Reject</Button>}
        {l.status !== 'REMOVED' && <Button variant="danger" isLoading={busy === `remove-${l.id}`} disabled={!!busy} onClick={() => { if (window.confirm(`Remove "${l.title}" permanently from the platform?`)) onAct('remove', l, `"${l.title}" removed.`); }} aria-label={`Remove ${l.title}`}>Remove</Button>}
      </div>
    </Card>
  );
}

function AdminQueue({ auth }) {
  const [filter, setFilter] = useState('PENDING_APPROVAL');
  const [items, setItems] = useState(null);
  const [counts, setCounts] = useState({});
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState('');
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [list, all] = await Promise.all([api.adminListings(auth.token, filter), api.adminListings(auth.token)]);
      setItems(list);
      const c = { '': all.length };
      all.forEach(l => { c[l.status] = (c[l.status] || 0) + 1; });
      setCounts(c);
    } catch (e) { setError(e.message); setItems(prev => prev || []); }
    finally { setLoading(false); }
  }, [auth, filter]);
  useEffect(() => { load(); }, [load]);

  async function onAct(kind, l, okMsg) {
    setBusy(`${kind}-${l.id}`); setMsg(''); setError('');
    try {
      const fn = kind === 'approve' ? api.approve : kind === 'reject' ? api.reject : api.adminRemove;
      await fn(auth.token, l.id);
      setMsg(okMsg); await load();
    } catch (e) { setError(e.message); }
    finally { setBusy(''); }
  }

  return (
    <section aria-labelledby="admin-h">
      <div className="dash-head">
        <div><h2 id="admin-h" style={{ margin: 0 }}>Moderation queue</h2></div>
        <Button variant="secondary" onClick={load} isLoading={loading} loadingText="Refreshing…">Refresh</Button>
      </div>
      <div className="seg" role="group" aria-label="Filter listings by status">
        {FILTERS.map(([v, t]) => <button key={v || 'all'} type="button" aria-pressed={filter === v} onClick={() => setFilter(v)}>{t}{counts[v] != null ? ` (${counts[v]})` : ''}</button>)}
      </div>
      <div className="tab-row" aria-live="polite">
        {msg && <Alert variant="success" onDismiss={() => setMsg('')}>{msg}</Alert>}
        {error && <Alert variant="error" onDismiss={() => setError('')}>{error}</Alert>}
      </div>
      {loading && items == null && <div aria-busy="true"><Spinner label="Loading listings…" /><div className="skeleton" /></div>}
      {items && items.length === 0 && !loading && <div className="empty">{filter === 'PENDING_APPROVAL' ? 'The queue is clear — no listings are waiting for approval.' : 'No listings match this filter.'}</div>}
      <div style={{ display: 'grid', gap: 'var(--sn-space-4)' }}>
        {items?.map(l => <ModerationCard key={l.id} l={l} busy={busy} onAct={onAct} />)}
      </div>
      {filter !== 'PENDING_APPROVAL' && items?.length > 0 && (
        <details style={{ marginTop: 'var(--sn-space-5)' }}>
          <summary>Compact table view</summary>
          <TableContainer label="All listings summary">
            <table><caption className="sn-visually-hidden">Listings by status</caption>
              <thead><tr><th scope="col">ID</th><th scope="col">Title</th><th scope="col">ZIP</th><th scope="col">Status</th><th scope="col">Complete</th></tr></thead>
              <tbody>{items.map(l => <tr key={l.id}><td>{l.id}</td><td>{l.title}</td><td>{l.zip}</td><td><StatusBadge status={l.status} /></td><td>{l.completeness?.score ?? 0}%</td></tr>)}</tbody>
            </table>
          </TableContainer>
        </details>
      )}
    </section>
  );
}

export default function AdminPage({ auth }) {
  return (
    <RoleGuard auth={auth} roles={['ADMIN']}
      loggedOut={<Alert variant="info">Log in as an administrator to moderate listings.</Alert>}
      denied={<Alert variant="error" title="Administrators only">Sign in with an administrator account.</Alert>}>
      <AdminQueue auth={auth} />
    </RoleGuard>
  );
}
