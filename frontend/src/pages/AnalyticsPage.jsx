// Frontend — Owner: Prajval Sudhir
// Feature: Trust, Reviews & Analytics — host/admin dashboards (30/60/90, zip).
import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { Alert, Button, Spinner, TableContainer } from '../components/ui/index.js';
import './dashboards.css';

const PERIODS = [30, 60, 90];
const money = v => `$${Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function BarChart({ rows, valueKey, title, format }) {
  const max = Math.max(...rows.map(r => Number(r[valueKey]) || 0), 1);
  return (
    <figure style={{ margin: 0 }}>
      <figcaption><strong>{title}</strong></figcaption>
      <ul className="chart-bars" aria-label={title}>
        {rows.map(r => {
          const v = Number(r[valueKey]) || 0;
          return <li key={r.zip}>
            <span>{r.zip}</span>
            <span className="chart-track" aria-hidden="true"><span className="chart-fill" style={{ display: 'block', width: `${(v / max) * 100}%` }} /></span>
            <span className="chart-val">{format ? format(v) : v}</span>
          </li>;
        })}
      </ul>
    </figure>
  );
}

export default function AnalyticsPage({ auth }) {
  const [days, setDays] = useState(30);
  const [zipInput, setZipInput] = useState('');
  const [zip, setZip] = useState('');
  const [zipError, setZipError] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const role = auth?.user?.role;
  const allowed = role === 'ADMIN' || role === 'HOST';

  const load = useCallback(async () => {
    if (!allowed) return;
    setLoading(true); setError('');
    try {
      const fn = role === 'ADMIN' ? api.adminAnalytics : api.hostAnalytics;
      setData(await fn(auth.token, days, zip));
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [auth, days, zip, role, allowed]);
  useEffect(() => { load(); }, [load]);

  if (!auth) return <Alert variant="info">Log in as a host or administrator to see analytics.</Alert>;
  if (!allowed) return <Alert variant="info" title="Not available for customers">Analytics are for hosts and administrators.</Alert>;

  function applyZip(e) {
    e.preventDefault();
    const z = zipInput.trim();
    if (z && !/^\d{5}(-\d{4})?$/.test(z)) { setZipError('Enter a 5-digit ZIP code, or leave blank for all.'); return; }
    setZipError(''); setZip(z);
  }
  const rows = data?.by_zip || [];
  const rentals = data?.total_rentals ?? rows.reduce((s, r) => s + (r.rentals || 0), 0);

  return (
    <section aria-labelledby="an-h">
      <div className="dash-head">
        <div><h2 id="an-h" style={{ margin: 0 }}>{role === 'ADMIN' ? 'Platform analytics' : 'Host analytics'}</h2>
          <p className="card-meta" style={{ margin: 0 }}>{role === 'ADMIN' ? 'All listings' : 'Your listings only'}{zip ? ` · ZIP ${zip}` : ''}</p></div>
        <form className="dash-controls" onSubmit={applyZip} noValidate>
          <div className="field-group">
            <span id="period-l" className="field-hint">Period</span>
            <div className="seg" role="group" aria-labelledby="period-l">
              {PERIODS.map(p => <button key={p} type="button" aria-pressed={days === p} onClick={() => setDays(p)}>{p} days</button>)}
            </div>
          </div>
          <div className="field-group">
            <label htmlFor="an-zip">ZIP filter</label>
            <input id="an-zip" inputMode="numeric" value={zipInput} onChange={e => setZipInput(e.target.value)} placeholder="95110 (blank = all)" aria-invalid={zipError ? 'true' : undefined} aria-describedby={zipError ? 'an-zip-err' : undefined} />
            {zipError && <span id="an-zip-err" className="field-error">{zipError}</span>}
          </div>
          <Button type="submit" isLoading={loading} loadingText="Loading…">Apply</Button>
          {zip && <Button variant="ghost" onClick={() => { setZip(''); setZipInput(''); setZipError(''); }}>Clear ZIP</Button>}
        </form>
      </div>

      <div aria-live="polite">{error && <Alert variant="error" onDismiss={() => setError('')}>{error}</Alert>}</div>
      {loading && !data && <div aria-busy="true"><Spinner label="Loading analytics…" /><div className="metric-grid"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div></div>}

      {data && <div aria-busy={loading ? 'true' : 'false'}>
        <dl className="metric-grid">
          <div className="metric"><dt>Rentals booked</dt><dd>{rentals}</dd></div>
          <div className="metric"><dt>Bookings</dt><dd>{data.total_bookings}</dd></div>
          <div className="metric"><dt>Revenue</dt><dd>{money(data.total_revenue)}</dd></div>
          <div className="metric"><dt>Period</dt><dd>{data.period_days} days</dd></div>
        </dl>
        {rows.length === 0 ? (
          <div className="empty">No bookings{zip ? ` in ZIP ${zip}` : ''} in the last {data.period_days} days.</div>
        ) : <>
          <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))' }}>
            <div className="metric"><BarChart rows={rows} valueKey="bookings" title="Bookings by ZIP" /></div>
            <div className="metric"><BarChart rows={rows} valueKey="revenue" title="Revenue by ZIP" format={money} /></div>
          </div>
          <TableContainer label="Analytics by ZIP code">
            <table>
              <caption className="sn-visually-hidden">Rentals, bookings and revenue by ZIP for the last {data.period_days} days</caption>
              <thead><tr><th scope="col">ZIP</th><th scope="col">Rentals</th><th scope="col">Bookings</th><th scope="col">Revenue</th></tr></thead>
              <tbody>{rows.map(r => <tr key={r.zip}><th scope="row">{r.zip}</th><td>{r.rentals}</td><td>{r.bookings}</td><td>{money(r.revenue)}</td></tr>)}</tbody>
              <tfoot><tr><th scope="row">Total</th><td>{rentals}</td><td>{data.total_bookings}</td><td>{money(data.total_revenue)}</td></tr></tfoot>
            </table>
          </TableContainer>
        </>}
      </div>}
    </section>
  );
}
