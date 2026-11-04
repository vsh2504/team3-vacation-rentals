import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client.js';
// Sprint 2 (Vinayak): detail = photos, amenities, cost, rating, reviews,
// # booked today, Book button (disabled when unavailable is enforced by
// the API: booking an unavailable listing returns 409).
export default function ListingDetailPage({ auth }) {
  const { id } = useParams();
  const [listing, setListing] = useState(null); const [reviews, setReviews] = useState(null);
  const [checkIn, setCheckIn] = useState(''); const [checkOut, setCheckOut] = useState(''); const [guests, setGuests] = useState(2);
  const [msg, setMsg] = useState(''); const [error, setError] = useState('');
  useEffect(() => {
    api.listing(id).then(setListing).catch(e => setError(e.message));
    api.listingReviews(id).then(setReviews).catch(() => {});
  }, [id]);
  async function book(e) {
    e.preventDefault(); setError(''); setMsg('');
    if (!auth) return setError('Log in as a Customer to book.');
    try {
      const b = await api.book(auth.token, { listing_id: Number(id), check_in: checkIn, check_out: checkOut, guests });
      setMsg(`Booked! Booking #${b.id}, total $${b.total_price}, status ${b.status}. See My Bookings.`);
    } catch (err) { setError(err.message); }
  }
  if (error && !listing) return <p role="alert">{error}</p>;
  if (!listing) return <p>Loading…</p>;
  return (
    <section>
      <h2>{listing.title}</h2>
      {listing.photos?.map((p, i) => <img key={i} src={p} alt={`${listing.title} photo ${i + 1}`} style={{ width: '100%', maxHeight: 260, objectFit: 'cover', borderRadius: 8, marginBottom: 8 }} />)}
      {!listing.photos?.length && <p><em>No photos yet — host photo upload (Blob) is Sprint 3.</em></p>}
      <p>{listing.address}, {listing.city}, {listing.state} {listing.zip}</p>
      <p>${listing.price_per_night}/night — up to {listing.max_guests} guests — {listing.bedrooms} bed, {listing.bathrooms} bath</p>
      <p>{listing.description}</p>
      <p>Amenities: {(listing.amenities || []).join(', ')}</p>
      <p>Available times: {listing.available_times}</p>
      <p># booked today: {listing.booked_today}</p>
      <p>Rating: {reviews?.average_rating ?? 'No reviews yet'} ({reviews?.count ?? 0} reviews)</p>
      <ul>{reviews?.reviews?.map(r => <li key={r.id}>⭐ {r.rating} — {r.comment}</li>)}</ul>
      <h3>Book this stay (max 14 days)</h3>
      <form onSubmit={book}>
        <label>Check-in <input required type="date" value={checkIn} onChange={e => setCheckIn(e.target.value)} /></label>{' '}
        <label>Check-out <input required type="date" value={checkOut} onChange={e => setCheckOut(e.target.value)} /></label>{' '}
        <label>Guests <input required type="number" min="1" value={guests} onChange={e => setGuests(Number(e.target.value))} /></label>{' '}
        <button type="submit">Book</button>
      </form>
      {msg && <p>{msg}</p>}{error && <p role="alert">{error}</p>}
    </section>
  );
}
