import React, { useState } from 'react';
import ListingCard from '../components/ListingCard.jsx';
import MapView from '../components/MapView.jsx';
import seed from '../../../backend/data/listings_seed.json';
// Week 1: seed import is a demo fallback only. Sprint 1 replaces it with
// api.search() and keeps the same ListingCard props.
export default function SearchPage({ role }) {
  const [zip, setZip] = useState('');
  const [guests, setGuests] = useState(2);
  const [error, setError] = useState('');
  const results = seed.filter(l => l.status === 'APPROVED' && (!zip || l.zip === zip) && l.max_guests >= guests);
  return (
    <section>
      <h2>Search vacation rentals (max stay 14 days)</h2>
      <label>Zip <input value={zip} onChange={e => setZip(e.target.value)} placeholder="95110" /></label>{' '}
      <label>Guests <input type="number" min="1" value={guests} onChange={e => setGuests(Number(e.target.value))} /></label>{' '}
      <label>Check-in <input type="date" /></label>{' '}
      <label>Check-out <input type="date" onChange={e => {
        // Week 1 UI hint only; the API enforces the 14-day rule (422).
        setError('');
      }} /></label>
      {error && <p role="alert">{error}</p>}
      <p>{results.length} approved listings match (seed data, Week 1).</p>
      <MapView listings={results} />
      <div>{results.map(l => <ListingCard key={l.id} listing={l} role={role} />)}</div>
    </section>
  );
}
