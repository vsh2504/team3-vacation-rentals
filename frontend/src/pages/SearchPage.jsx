// Frontend — Owner: Vinayak Gupta (team lead)
// Feature: Find a Stay — search page (filters, results, map).
import React, { useEffect, useRef, useState } from 'react';
import ListingCard from '../components/ListingCard.jsx';
import MapView from '../components/MapView.jsx';
import { api, qs } from '../api/client.js';
import { PlaceSuggestions, usePlacesAutocomplete } from '../usePlacesAutocomplete.jsx';
import seed from '../../../backend/data/listings_seed.json';

const DAY = 86400000;
const nightsBetween = (a, b) => Math.round((new Date(b) - new Date(a)) / DAY);

function validate(f) {
  const e = {};
  if (!(Number(f.guests) >= 1)) e.guests = 'Enter at least 1 guest.';
  if (f.checkIn && !f.checkOut) e.checkOut = 'Choose a check-out date.';
  if (f.checkOut && !f.checkIn) e.checkIn = 'Choose a check-in date.';
  if (f.checkIn && f.checkOut) {
    const n = nightsBetween(f.checkIn, f.checkOut);
    if (n <= 0) e.checkOut = 'Check-out must be after check-in.';
    else if (n > 14) e.checkOut = `Stays are limited to 14 nights (you chose ${n}).`;
  }
  return e;
}

const Field = ({ id, label, error: er, hint, wide, children }) => (
  <div className={`field-group${wide ? ' field-group-wide' : ''}`}>
    <label htmlFor={id}>{label}</label>
    {children}
    {hint && !er && <span className="field-hint" id={`${id}-hint`}>{hint}</span>}
    {er && <span className="field-error" id={`${id}-err`} role="alert">{er}</span>}
  </div>
);

export default function SearchPage() {
  const [f, setF] = useState({ checkIn: '', checkOut: '', checkInTime: '', checkOutTime: '', guests: 2, city: '', state: '', zip: '', address: '' });
  const [errors, setErrors] = useState({});
  const [results, setResults] = useState([]);
  const [status, setStatus] = useState('idle'); // idle | loading | done
  const [error, setError] = useState('');
  const [source, setSource] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [geoMsg, setGeoMsg] = useState('');
  const [picked, setPicked] = useState(null);
  const [view, setView] = useState('list');
  const set = k => e => setF(p => ({ ...p, [k]: e.target.value }));
  const nights = f.checkIn && f.checkOut ? nightsBetween(f.checkIn, f.checkOut) : null;
  const detailSearch = qs({ check_in: f.checkIn, check_out: f.checkOut, check_in_time: f.checkInTime, check_out_time: f.checkOutTime, guests: f.guests });
  const errRef = useRef(null);

  async function run(e, override) {
    if (e) e.preventDefault();
    const v = validate(f);
    setErrors(v);
    if (Object.keys(v).length) { setError('Please fix the highlighted fields.'); return; }
    setError(''); setStatus('loading'); setSelectedId(null);
    const addr = override ?? f.address;
    const params = { check_in: f.checkIn, check_out: f.checkOut, check_in_time: f.checkInTime, check_out_time: f.checkOutTime,
      guests: f.guests, city: f.city, state: f.state, zip: f.zip, address: addr, include_unavailable: f.checkIn ? true : '' };
    try {
      const data = await api.search(params);
      setResults(Array.isArray(data) ? data : []); setSource('API');
    } catch (err) {
      if (/network|failed to fetch|Request failed/i.test(err.message) || err instanceof TypeError) {
        setError(`${err.message} — showing sample listings instead.`);
        setResults(seed.filter(l => l.status === 'APPROVED' && (!f.zip || l.zip === f.zip)
          && (!f.city || l.city.toLowerCase() === f.city.toLowerCase())
          && (!f.state || l.state.toLowerCase() === f.state.toLowerCase()) && l.max_guests >= f.guests));
        setSource('sample data fallback');
      } else { setError(err.message); setResults([]); setSource(''); }
    } finally { setStatus('done'); }
  }
  useEffect(() => { run(); }, []); // eslint-disable-line

  const addrAC = usePlacesAutocomplete((p) => {
    setPicked({ display_name: p.formatted, city: p.city, state: p.state, zip: p.zip, lat: p.lat, lng: p.lng, provider: 'google' });
    setGeoMsg(`Selected: ${p.formatted}`);
    setF(prev => ({ ...prev, address: p.formatted, city: p.city || prev.city, state: p.state || prev.state, zip: p.zip || prev.zip }));
  });
  // City suggestions: picking one fills city + state (address/ZIP cleared so they don't over-constrain).
  const cityAC = usePlacesAutocomplete((p) => {
    setF(prev => ({ ...prev, city: p.city || prev.city, state: p.state || prev.state, zip: '', address: '' }));
    setPicked(null);
  }, { types: ['locality'] });

  async function lookup() {
    setGeoMsg(''); setSuggestions([]);
    if (f.address.trim().length < 3) { setGeoMsg('Type at least 3 characters of an address.'); return; }
    setGeoMsg('Looking up address…');
    try {
      const r = await api.geocode(f.address);
      setSuggestions([r]); setGeoMsg(`1 match from ${r.provider || 'address provider'}.`);
    } catch (err) { setGeoMsg(err.message); }
  }
  function choose(s) {
    setPicked(s); setSuggestions([]); setGeoMsg(`Selected: ${s.display_name}`);
    setF(p => ({ ...p, address: s.display_name, city: s.city || p.city, state: s.state || p.state, zip: s.zip || p.zip }));
  }

  const aria = (id, er, hint) => ({ id, 'aria-invalid': er ? 'true' : undefined, 'aria-describedby': er ? `${id}-err` : hint ? `${id}-hint` : undefined });

  return (
    <section>
      <h2 className="page-title">Find a stay</h2>
      <form onSubmit={run} className="search-bar" noValidate aria-label="Search vacation rentals">
        <div className="search-main">
          <Field id="s-city" label="City" ><input id="s-city" value={f.city} onChange={e => { set('city')(e); cityAC.query(e.target.value); }} placeholder="Where to? e.g. San Jose" autoComplete="address-level2" /><PlaceSuggestions ac={cityAC} label="City suggestions" /></Field>
          <Field id="s-in" label="Check-in date" error={errors.checkIn}><input type="date" {...aria('s-in', errors.checkIn)} value={f.checkIn} onChange={set('checkIn')} /></Field>
          <Field id="s-out" label="Check-out date" error={errors.checkOut}><input type="date" {...aria('s-out', errors.checkOut, true)} value={f.checkOut} min={f.checkIn || undefined} onChange={set('checkOut')} /></Field>
          <Field id="s-g" label="Guests" error={errors.guests}><input type="number" min="1" {...aria('s-g', errors.guests)} value={f.guests} onChange={e => setF(p => ({ ...p, guests: Number(e.target.value) }))} /></Field>
          <button type="submit" className="search-submit" disabled={status === 'loading'} aria-busy={status === 'loading'}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><line x1="20" y1="20" x2="16.5" y2="16.5" /></svg>
            <span>{status === 'loading' ? 'Searching…' : 'Search'}</span>
          </button>
        </div>
        <div className="search-more">
          <Field id="s-in-t" label="Check-in time"><input type="time" id="s-in-t" value={f.checkInTime} onChange={set('checkInTime')} /></Field>
          <Field id="s-out-t" label="Check-out time"><input type="time" id="s-out-t" value={f.checkOutTime} onChange={set('checkOutTime')} /></Field>
          <Field id="s-state" label="State"><input id="s-state" value={f.state} onChange={set('state')} placeholder="CA" autoComplete="address-level1" /></Field>
          <Field id="s-zip" label="ZIP"><input id="s-zip" value={f.zip} onChange={set('zip')} placeholder="95110" inputMode="numeric" autoComplete="postal-code" /></Field>
          <Field id="s-addr" wide label="Address">
            <div style={{ position: 'relative' }}>
            <div className="input-row">
              <input id="s-addr" aria-describedby="s-addr-hint s-addr-msg" value={f.address} onChange={e => { set('address')(e); setPicked(null); addrAC.query(e.target.value); }} placeholder="100 Main St, San Jose" autoComplete="street-address" />
              <button type="button" className="btn btn-ghost btn-sm" onClick={lookup}>Look up</button>
            </div>
            <PlaceSuggestions ac={addrAC} label="Address suggestions" />
            </div>
            <span id="s-addr-msg" role="status" className="field-hint">{geoMsg}</span>
            {suggestions.length > 0 && (
              <ul role="listbox" aria-label="Address suggestions" style={{ listStyle: 'none', padding: 0, margin: '4px 0' }}>
                {suggestions.map((s, i) => (
                  <li key={i} role="option" aria-selected={picked === s}>
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => choose(s)}>{s.display_name}</button>
                  </li>
                ))}
              </ul>
            )}
          </Field>
        </div>
      </form>
      {nights > 0 && nights <= 14 && <p className="card-meta">{nights} night{nights === 1 ? '' : 's'} selected.</p>}
      {error && <p role="alert" className="alert alert-danger" ref={errRef}>{error}</p>}
      <p role="status" aria-live="polite" className="status-line">
        {status === 'loading' ? 'Searching…' : status === 'done' ? `${results.length} stay${results.length === 1 ? '' : 's'}${source === 'API' ? '' : ' (sample data)'}` : ''}
      </p>
      <div role="group" aria-label="Results view" className="view-toggle">
        <button type="button" className="btn btn-sm btn-ghost" aria-pressed={view === 'list'} onClick={() => setView('list')}>List</button>
        <button type="button" className="btn btn-sm btn-ghost" aria-pressed={view === 'map'} onClick={() => setView('map')}>Map</button>
      </div>
      {status === 'done' && !results.length && !error && (
        <p className="alert">No listings match. Try different dates, fewer guests, or a wider location.</p>
      )}
      <div className={`search-layout view-${view}`}>
        <div className="results-grid">
          {results.map((l, i) => (
            <ListingCard key={l.id} listing={l} index={i} selected={l.id === selectedId} onSelect={id => { setSelectedId(id); setView('map'); }} search={detailSearch} />
          ))}
        </div>
        <div className="map-pane" hidden={view === 'list'}>
          <MapView listings={results} selectedId={selectedId} onSelect={setSelectedId} />
        </div>
      </div>
    </section>
  );
}
