// Frontend — Owner: Manoj (Manoj Ganjigatte Manjunatha)
// Feature: Book & Cancel a Stay — my bookings, cancel, complete.
// Review form inside this page is Prajval's ReviewForm component, not this file.
import React, { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import ReviewForm from '../components/ReviewForm.jsx';
import { Link } from 'react-router-dom';
// Sprint 1-2 (Manoj/Prajval): my bookings, cancel, complete (past stays),
// review completed bookings. Past + upcoming are separated by check_out.
export default function BookingsPage({ auth }) {
  const [bookings, setBookings] = useState([]); const [msg, setMsg] = useState(''); const [error, setError] = useState('');
  function load() { if (auth) api.myBookings(auth.token).then(setBookings).catch(e => setError(e.message)); }
  useEffect(load, [auth]);
  if (!auth) return <p>Log in to see your bookings.</p>;
  const today = new Date().toISOString().slice(0, 10);
  const upcoming = bookings.filter(b => b.status === 'CONFIRMED' && b.check_out >= today);
  const past = bookings.filter(b => b.check_out < today || b.status === 'COMPLETED');
  const other = bookings.filter(b => !upcoming.includes(b) && !past.includes(b));
  async function act(fn, id, okMsg) { setError(''); try { await fn(auth.token, id); setMsg(okMsg); load(); } catch (err) { setError(err.message); } }
  const row = (b) => (
    <article className="page-card">
      <strong>Booking #{b.id}</strong> — listing #{b.listing_id} — {b.check_in} → {b.check_out} — {b.guests} guests — ${b.total_price} — {b.status}
      <div>
        {b.status === 'CONFIRMED' && <><button onClick={() => act(api.cancelBooking, b.id, 'Booking cancelled — dates are free again.')}>Cancel</button>{' '}
          {b.check_out < today && <button onClick={() => act(api.completeBooking, b.id, 'Stay marked completed — you can now review it.')}>Mark completed</button>}</>}
        {b.status === 'COMPLETED' && <>
          <ReviewForm auth={auth} bookingId={b.id} onSubmitted={() => { setMsg(`Review submitted for booking #${b.id}.`); load(); }} />{' '}
          <Link to={`/listings/${b.listing_id}`}>View listing</Link>
        </>}
      </div>
    </article>
  );
  return (
    <section>
      <h2>My bookings</h2>
      <h3>Upcoming</h3>{upcoming.length ? upcoming.map(row) : <p>None.</p>}
      <h3>Past / completed</h3>{past.length ? past.map(row) : <p>None. Tip: to demo a review, book past dates, mark completed, then review.</p>}
      {other.length > 0 && <><h3>Other</h3>{other.map(row)}</>}
      {msg && <p>{msg}</p>}{error && <p role="alert">{error}</p>}
    </section>
  );
}
