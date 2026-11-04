// Frontend — Owner: Vinayak Gupta (team lead)
// Feature: Find a Stay — search page (filters, results, map).
import React, { useEffect, useState } from 'react';
import ListingCard from '../components/ListingCard.jsx';
import MapView from '../components/MapView.jsx';
import { api } from '../api/client.js';
import seed from '../../../backend/data/listings_seed.json';
// Sprint 1-2 (Vinayak): search calls the API, not the seed.
// Seed is only the fallback if the API is not running.
export default function SearchPage() {
  const [zip, setZip] = useState(''); const [city, setCity] = useState(''); const [state, setState] = useState('');
  const [guests, setGuests] = useState(2); const [checkIn, setCheckIn] = useState(''); const [checkOut, setCheckOut] = useState('');
  const [results, setResults] = useState([]); const [error, setError] = useState(''); const [source, setSource] = useState('');
  async function run(e) {
    if (e) e.preventDefault();
    if (checkIn && checkOut) {
      const nights = (new Date(checkOut) - new Date(checkIn)) / 86400000;
      if (nights <= 0) return setError('Check-out must be after check-in.');
      if (nights > 14) return setError('Stay cannot exceed 14 days (API will also return 422).');
    }
    setError('');
    try {
      const data = await api.search({ zip, city, state, guests, check_in: checkIn, check_out: checkOut });
      setResults(data); setSource('API');
    } catch (err) {
      setError(`${err.message} — showing seed fallback.`);
      setResults(seed.filter(l => l.status === 'APPROVED' && (!zip || l.zip === zip) && (!city || l.city.toLowerCase() === city.toLowerCase()) && l.max_guests >= guests));
      setSource('seed fallback');
    }
  }
  useEffect(() => { run(); }, []);
  return (
    <section>
      <h2>Search vacation rentals (max stay 14 days)</h2>
      <form onSubmit={run}>
        <label>Zip <input value={zip} onChange={e => setZip(e.target.value)} placeholder="95110" /></label>{' '}
        <label>City <input value={city} onChange={e => setCity(e.target.value)} placeholder="San Jose" /></label>{' '}
        <label>State <input value={state} onChange={e => setState(e.target.value)} placeholder="CA" /></label>{' '}
        <label>Guests <input type="number" min="1" value={guests} onChange={e => setGuests(Number(e.target.value))} /></label>{' '}
        <label>Check-in <input type="date" value={checkIn} onChange={e => setCheckIn(e.target.value)} /></label>{' '}
        <label>Check-out <input type="date" value={checkOut} onChange={e => setCheckOut(e.target.value)} /></label>{' '}
        <button type="submit">Search</button>
      </form>
      {error && <p role="alert">{error}</p>}
      <p>{results.length} listings match ({source}).</p>
      <MapView listings={results} />
      <div>{results.map(l => <ListingCard key={l.id} listing={l} />)}</div>
    </section>
  );
}
