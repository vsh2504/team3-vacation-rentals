// Frontend — Owner: Vinayak Gupta (team lead)
// Feature: Find a Stay — listing detail (photos, amenities, cost, rating, reviews, # booked today).
// Booking form inside this page is Manoj's BookingForm component, not this file.
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client.js';
import BookingForm from '../components/BookingForm.jsx';
// Sprint 2 (Vinayak): detail = photos, amenities, cost, rating, reviews,
// # booked today, Book button (disabled when unavailable is enforced by
// the API: booking an unavailable listing returns 409).
export default function ListingDetailPage({ auth }) {
  const { id } = useParams();
  const [listing, setListing] = useState(null); const [reviews, setReviews] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    api.listing(id).then(setListing).catch(e => setError(e.message));
    api.listingReviews(id).then(setReviews).catch(() => {});
  }, [id]);
  if (error && !listing) return <p role="alert">{error}</p>;
  if (!listing) return <p>Loading…</p>;
  return (
    <section>
      <h2>{listing.title}</h2>
      <p className="card-meta">{listing.address}, {listing.city}, {listing.state} {listing.zip}</p>
      {listing.photos?.map((p, i) => <img key={i} src={p} alt={`${listing.title} photo ${i + 1}`} style={{ width: '100%', maxHeight: 260, objectFit: 'cover', borderRadius: 8, marginBottom: 8 }} />)}
      {!listing.photos?.length && <p><em>No photos yet — host photo upload (Blob) is Sprint 3.</em></p>}
      {listing.videos?.map((v, i) => <video key={i} src={v} controls style={{ width: '100%', maxHeight: 260, borderRadius: 8, marginBottom: 8 }} />)}
      {!listing.videos?.length && <p><em>No videos yet for this listing.</em></p>}
      <p>${listing.price_per_night}/night — up to {listing.max_guests} guests — {listing.bedrooms} bed, {listing.bathrooms} bath</p>
      <p>{listing.description}</p>
      <p>Amenities: {(listing.amenities || []).join(', ')}</p>
      <p>Available times: {listing.available_times}</p>
      <p># booked today: {listing.booked_today}</p>
      <p>Rating: {reviews?.average_rating ?? 'No reviews yet'} ({reviews?.count ?? 0} reviews)</p>
      <ul>{reviews?.reviews?.map(r => <li key={r.id}>⭐ {r.rating} — {r.comment}</li>)}</ul>
      <BookingForm auth={auth} listingId={id} />
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
