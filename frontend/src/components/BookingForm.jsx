// Frontend — Owner: Manoj (Manoj Ganjigatte Manjunatha)
// Feature: Book & Cancel a Stay — booking form component.
// Used by ListingDetailPage (Vinayak's page) so the booking flow is
// Manoj's code even when it is rendered inside another feature's page.
// Rules are NOT enforced here — the API returns 409 (overlap) / 422
// (14-day, guest cap) and this component shows that message verbatim.
import React, { useState } from 'react';
import { api } from '../api/client.js';
export default function BookingForm({ auth, listingId }) {
  const [checkIn, setCheckIn] = useState(''); const [checkOut, setCheckOut] = useState(''); const [guests, setGuests] = useState(2);
  const [msg, setMsg] = useState(''); const [error, setError] = useState('');
  async function book(e) {
    e.preventDefault(); setError(''); setMsg('');
    if (!auth) return setError('Log in as a Customer to book.');
    try {
      const b = await api.book(auth.token, { listing_id: Number(listingId), check_in: checkIn, check_out: checkOut, guests });
      setMsg(`Booked! Booking #${b.id}, total $${b.total_price}, status ${b.status}. See My Bookings.`);
    } catch (err) { setError(err.message); }
  }
  return (
    <div>
      <h3>Book this stay (max 14 days)</h3>
      <form onSubmit={book}>
        <label>Check-in <input required type="date" value={checkIn} onChange={e => setCheckIn(e.target.value)} /></label>{' '}
        <label>Check-out <input required type="date" value={checkOut} onChange={e => setCheckOut(e.target.value)} /></label>{' '}
        <label>Guests <input required type="number" min="1" value={guests} onChange={e => setGuests(Number(e.target.value))} /></label>{' '}
        <button type="submit">Book</button>
      </form>
      {msg && <p>{msg}</p>}{error && <p role="alert">{error}</p>}
    </div>
  );
}
