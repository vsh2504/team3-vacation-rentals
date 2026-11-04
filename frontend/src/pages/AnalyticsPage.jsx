// Frontend — Owner: Prajval Sudhir
// Feature: Trust, Reviews & Analytics — host/admin dashboards (30/60/90, zip).
import React, { useEffect, useState } from 'react';
import { api } from '../api/client.js';
// Sprint 3 (Prajval): host + admin analytics, by zip, 30/60/90 days.
// Host sees only their listings (API scope); admin sees platform totals.
export default function AnalyticsPage({ auth }) {
  const [days, setDays] = useState(30); const [zip, setZip] = useState('');
  const [data, setData] = useState(null); const [error, setError] = useState('');
  function load() {
    if (!auth) return;
    const fn = auth.user.role === 'ADMIN' ? api.adminAnalytics : api.hostAnalytics;
    fn(auth.token, days, zip).then(setData).catch(e => setError(e.message));
  }
  useEffect(load, [auth, days]);
  if (!auth) return <p>Log in to see analytics.</p>;
  if (auth.user.role === 'CUSTOMER') return <p>Analytics are for Hosts (own listings) and Admins (platform). Customers see reviews on listing pages.</p>;
  return (
    <section>
      <h2>{auth.user.role === 'ADMIN' ? 'Platform analytics' : 'Host analytics'}</h2>
      <label>Period <select value={days} onChange={e => setDays(Number(e.target.value))}><option value={30}>30 days</option><option value={60}>60 days</option><option value={90}>90 days</option></select></label>{' '}
      <label>Zip <input value={zip} onChange={e => setZip(e.target.value)} placeholder="95110 (blank = all)" /></label>{' '}
      <button onClick={load}>Refresh</button>
      {error && <p role="alert">{error}</p>}
      {data && <>
        <p>Total bookings: {data.total_bookings} — Total revenue: ${data.total_revenue} — Period: {data.period_days} days</p>
        <table style={{ borderCollapse: 'collapse' }}>
          <thead><tr><th style={{ border: '1px solid #ccc', padding: 6 }}>Zip</th><th style={{ border: '1px solid #ccc', padding: 6 }}>Rentals (distinct listings)</th><th style={{ border: '1px solid #ccc', padding: 6 }}>Bookings</th><th style={{ border: '1px solid #ccc', padding: 6 }}>Revenue</th></tr></thead>
          <tbody>{data.by_zip.map(r => <tr key={r.zip}><td style={{ border: '1px solid #ccc', padding: 6 }}>{r.zip}</td><td style={{ border: '1px solid #ccc', padding: 6 }}>{r.rentals}</td><td style={{ border: '1px solid #ccc', padding: 6 }}>{r.bookings}</td><td style={{ border: '1px solid #ccc', padding: 6 }}>${r.revenue}</td></tr>)}</tbody>
        </table>
        {data.by_zip.length === 0 && <p>No bookings in this period. Bookings count from booked_date, cancelled bookings are excluded.</p>}
      </>}
    </section>
  );
}
