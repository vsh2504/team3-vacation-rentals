// Frontend — Owner: Vinayak Gupta (team lead)
// Feature: Find a Stay — listing detail (media, amenities, cost, rating, reviews, # booked today, map).
// Booking form inside this page is Manoj's BookingForm component, not this file.
import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api/client.js';
import BookingForm from '../components/BookingForm.jsx';
import MapView from '../components/MapView.jsx';

const money = v => (v == null ? '—' : `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`);

export default function ListingDetailPage({ auth }) {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const q = Object.fromEntries(['check_in', 'check_out', 'check_in_time', 'check_out_time', 'guests'].map(k => [k, sp.get(k)]).filter(([, v]) => v));
  const [listing, setListing] = useState(null);
  const [reviews, setReviews] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const key = JSON.stringify(q);

  useEffect(() => {
    setLoading(true); setError('');
    api.listing(id, q).then(setListing).catch(e => setError(e.message)).finally(() => setLoading(false));
    api.listingReviews(id).then(setReviews).catch(() => setReviews(null));
  }, [id, key]); // eslint-disable-line

  if (loading) return <p role="status">Loading listing…</p>;
  if (error && !listing) return <p role="alert" className="alert alert-danger">{error}</p>;
  if (!listing) return null;

  const av = listing.availability || {};
  const available = listing.available ?? true;
  const requested = !!av.requested;
  const list = reviews?.reviews || listing.reviews || [];
  const avg = reviews?.average_rating ?? listing.average_rating;
  const count = reviews?.count ?? listing.review_count ?? list.length;

  return (
    <section>
      <h2>{listing.title}</h2>
      <p className="card-meta">{listing.address}, {listing.city}, {listing.state} {listing.zip}</p>
      <p>
        <span className={`badge ${available ? 'badge-success' : 'badge-danger'}`}>
          {available ? (requested ? 'Available for your dates' : 'Available to book') : 'Unavailable'}
        </span>{' '}
        <span className="card-meta">★ {avg ?? 'No ratings'} ({count} reviews) · Booked today: {listing.booked_today ?? 0}</span>
      </p>
      {!available && av.reason && <p role="status" className="alert">{av.reason}</p>}

      <div className="media-gallery" style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))' }}>
        {listing.photos?.map((p, i) => <img key={i} src={p} alt={`${listing.title} photo ${i + 1}`} loading="lazy" style={{ width: '100%', height: 240, objectFit: 'cover', borderRadius: 8 }} />)}
        {listing.videos?.map((v, i) => <video key={i} src={v} controls preload="metadata" aria-label={`${listing.title} video ${i + 1}`} style={{ width: '100%', height: 240, borderRadius: 8, background: '#000' }} />)}
      </div>
      {!listing.photos?.length && !listing.videos?.length && <p><em>No photos or videos yet.</em></p>}

      <h3>Price</h3>
      <p>{money(listing.price_per_night)} per night{listing.total_cost != null && <> · <strong>{money(listing.total_cost)}</strong> total for {listing.nights} night{listing.nights === 1 ? '' : 's'}</>}</p>
      <p className="card-meta">Up to {listing.max_guests} guests · {listing.bedrooms} bed · {listing.bathrooms} bath</p>
      {(listing.check_in_time || listing.operating_start_time) && (
        <p className="card-meta">Check-in {listing.check_in_time || '—'} · Check-out {listing.check_out_time || '—'} · Hours {listing.operating_start_time || '—'}–{listing.operating_end_time || '—'}</p>
      )}
      {listing.available_times && <p className="card-meta">{listing.available_times}</p>}

      <h3>About</h3>
      <p>{listing.description}</p>
      <h3>Amenities</h3>
      {listing.amenities?.length ? <ul>{listing.amenities.map(a => <li key={a}>{a}</li>)}</ul> : <p>None listed.</p>}

      <h3>Location</h3>
      <MapView listings={[listing]} selectedId={listing.id} />

      <h3>Reviews</h3>
      {list.length ? <ul>{list.map(r => <li key={r.id}><span aria-label={`${r.rating} out of 5 stars`}>★ {r.rating}</span> — {r.comment}</li>)}</ul> : <p>No reviews yet.</p>}

      <h3>Book</h3>
      {available
        ? <BookingForm auth={auth} listingId={id} />
        : <button type="button" className="btn" disabled aria-disabled="true">Unavailable for these dates</button>}
    </section>
  );
}
