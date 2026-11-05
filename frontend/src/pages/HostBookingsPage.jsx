// Host view: who booked which of my properties, with customer contact and their review.
import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import { Alert, Badge, Card, Spinner } from '../components/ui/index.js';

const TABS = [
  { key: 'all', label: 'All' },
  { key: 'upcoming', label: 'Upcoming' },
  { key: 'past', label: 'Past' },
  { key: 'cancelled', label: 'Cancelled' },
];

function Stars({ n }) {
  return <span aria-label={`${n} out of 5 stars`} style={{ color: 'var(--sn-accent, #f2b134)' }}>{'★'.repeat(n)}{'☆'.repeat(5 - n)}</span>;
}

export default function HostBookingsPage({ auth }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('all');
  const [property, setProperty] = useState('');

  useEffect(() => {
    if (!auth) { setLoading(false); return; }
    setLoading(true);
    api.hostBookings(auth.token)
      .then((d) => setRows(Array.isArray(d) ? d : []))
      .catch((e) => setError(e.message || 'Failed to load bookings.'))
      .finally(() => setLoading(false));
  }, [auth]);

  const properties = useMemo(() => {
    const m = new Map();
    rows.forEach((r) => m.set(r.listing.id, r.listing.title));
    return [...m.entries()];
  }, [rows]);

  if (!auth || auth.user?.role !== 'HOST') {
    return (
      <section aria-labelledby="hb-heading">
        <h2 id="hb-heading">Bookings on my properties</h2>
        <Card><div className="empty-state" style={{ margin: 0 }}>
          <h3>Host sign-in required</h3>
          <Link to="/auth" className="btn btn-primary">Sign In / Register</Link>
        </div></Card>
      </section>
    );
  }

  const shown = rows.filter((r) => (tab === 'all' || r.stay_state === tab) && (!property || String(r.listing.id) === property));
  const reviews = rows.filter((r) => r.review);
  const avg = reviews.length ? (reviews.reduce((a, r) => a + r.review.rating, 0) / reviews.length).toFixed(1) : '—';
  const active = rows.filter((r) => r.status !== 'CANCELLED').length;

  return (
    <section aria-labelledby="hb-heading">
      <h2 id="hb-heading">Bookings on my properties</h2>
      <p className="card-meta">See which property was booked, who booked it, how to reach them, and the review they left.</p>

      {error && <Alert variant="error">{error}</Alert>}
      {loading ? <Spinner label="Loading bookings…" /> : (
        <>
          <p className="card-meta" role="status">
            {rows.length} booking(s) · {active} active · {reviews.length} review(s) · average rating {avg}
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center', margin: '0.75rem 0' }}>
            {TABS.map((t) => (
              <button key={t.key} type="button" onClick={() => setTab(t.key)}
                className={`btn btn-sm ${tab === t.key ? 'btn-primary' : 'btn-ghost'}`} aria-pressed={tab === t.key}>
                {t.label}
              </button>
            ))}
            <label htmlFor="hb-prop" className="card-meta" style={{ marginLeft: 'auto' }}>Property</label>
            <select id="hb-prop" style={{ width: 'auto', minWidth: 200, maxWidth: '100%' }} value={property} onChange={(e) => setProperty(e.target.value)}>
              <option value="">All properties</option>
              {properties.map(([id, title]) => <option key={id} value={id}>{title}</option>)}
            </select>
          </div>

          {shown.length === 0 ? (
            <Card><div className="empty-state" style={{ margin: 0 }}><h3>No bookings to show</h3>
              <p>Bookings made by customers on your approved listings will appear here.</p></div></Card>
          ) : (
            <div style={{ display: 'grid', gap: '0.75rem' }}>
              {shown.map((b) => (
                <Card key={b.id}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
                    <div>
                      <h3 style={{ margin: 0 }}><Link to={`/listings/${b.listing.id}`}>{b.listing.title}</Link></h3>
                      <p className="card-meta" style={{ margin: '0.25rem 0' }}>
                        {b.listing.city}, {b.listing.state} {b.listing.zip}
                      </p>
                    </div>
                    <div>
                      {b.status === 'CANCELLED' ? <Badge variant="danger">CANCELLED</Badge>
                        : b.status === 'COMPLETED' ? <Badge variant="accent">COMPLETED</Badge>
                        : b.stay_state === 'past' ? <Badge variant="neutral">STAY ENDED</Badge>
                        : <Badge variant="success">UPCOMING</Badge>}
                    </div>
                  </div>
                  <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: '0.5rem 1.5rem', margin: '0.75rem 0 0' }}>
                    <div style={{ minWidth: 0 }}><dt className="card-meta">Booked by</dt><dd style={{ margin: 0 }}><strong>{b.customer.full_name}</strong></dd></div>
                    <div style={{ minWidth: 0 }}><dt className="card-meta">Customer email</dt><dd style={{ margin: 0, overflowWrap: 'anywhere' }}>
                      {b.customer.email ? <a href={`mailto:${b.customer.email}`}>{b.customer.email}</a> : '—'}</dd></div>
                    <div style={{ minWidth: 0 }}><dt className="card-meta">Stay</dt><dd style={{ margin: 0 }}>{b.check_in} → {b.check_out}</dd></div>
                    <div style={{ minWidth: 0 }}><dt className="card-meta">Guests · Total</dt><dd style={{ margin: 0 }}>{b.guests} · ${b.total_price}</dd></div>
                    <div style={{ minWidth: 0 }}><dt className="card-meta">Booked on</dt><dd style={{ margin: 0 }}>{b.booked_date}</dd></div>
                  </dl>
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--sn-line)' }}>
                    {b.review ? (
                      <><Stars n={b.review.rating} />{' '}<span className="card-meta">review from {b.customer.full_name}</span>
                        {b.review.comment && <p style={{ margin: '0.25rem 0 0' }}>“{b.review.comment}”</p>}</>
                    ) : (
                      <span className="card-meta">{b.status === 'CANCELLED' ? 'No review (cancelled).' : 'No review yet.'}</span>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
