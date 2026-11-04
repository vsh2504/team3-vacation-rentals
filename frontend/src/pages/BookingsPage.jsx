import React, { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { Link } from 'react-router-dom';
// Sprint 1-2 (Manoj/Prajval): my bookings, cancel, complete (past stays),
// review completed bookings. Past + upcoming are separated by check_out.
export default function BookingsPage({ auth }) {
  const [bookings, setBookings] = useState([]); const [msg, setMsg] = useState(''); const [error, setError] = useState('');
  const [review, setReview] = useState({}); // bookingId -> {rating, comment}
  function load() { if (auth) api.myBookings(auth.token).then(setBookings).catch(e => setError(e.message)); }
  useEffect(load, [auth]);
  if (!auth) return <p>Log in to see your bookings.</p>;
  const today = new Date().toISOString().slice(0, 10);
  const upcoming = bookings.filter(b => b.status === 'CONFIRMED' && b.check_out >= today);
  const past = bookings.filter(b => b.check_out < today || b.status === 'COMPLETED');
  const other = bookings.filter(b => !upcoming.includes(b) && !past.includes(b));
  async function act(fn, id, okMsg) { setError(''); try { await fn(auth.token, id); setMsg(okMsg); load(); } catch (err) { setError(err.message); } }
  async function submitReview(b) {
    const r = review[b.id] || { rating: 5, comment: '' };
    try { await api.review(auth.token, { booking_id: b.id, rating: Number(r.rating), comment: r.comment }); setMsg(`Review submitted for booking #${b.id}.`); load(); }
    catch (err) { setError(err.message); }
  }
  const row = (b) => (
    <article key={b.id} style={{ border: '1px solid #ddd', padding: 12, margin: '12px 0' }}>
      <strong>Booking #{b.id}</strong> — listing #{b.listing_id} — {b.check_in} → {b.check_out} — {b.guests} guests — ${b.total_price} — {b.status}
      <div>
        {b.status === 'CONFIRMED' && <><button onClick={() => act(api.cancelBooking, b.id, 'Booking cancelled — dates are free again.')}>Cancel</button>{' '}
          {b.check_out < today && <button onClick={() => act(api.completeBooking, b.id, 'Stay marked completed — you can now review it.')}>Mark completed</button>}</>}
        {b.status === 'COMPLETED' && <>
          <label>Rating <select value={(review[b.id] || {}).rating || 5} onChange={e => setReview(r => ({ ...r, [b.id]: { ...(r[b.id] || { comment: '' }), rating: e.target.value } }))}><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>{' '}
          <label>Comment <input value={(review[b.id] || {}).comment || ''} onChange={e => setReview(r => ({ ...r, [b.id]: { ...(r[b.id] || { rating: 5 }), comment: e.target.value } }))} /></label>{' '}
          <button onClick={() => submitReview(b)}>Submit review</button>{' '}
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
