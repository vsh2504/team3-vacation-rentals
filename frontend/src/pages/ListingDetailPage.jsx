// Frontend — Owner: Vinayak Gupta (team lead)
// Feature: Find a Stay — listing detail (media, amenities, cost, rating, reviews, # booked today, map).
// Booking form inside this page is Manoj's BookingForm component, not this file.
import React, { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
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

  const photos = listing.photos || [];
  const shown = photos.slice(0, 3);
  return (
    <section className="detail">
      <h2 className="detail-title">{listing.title}</h2>
      <p className="detail-sub">
        <span aria-label={avg != null ? `Rated ${avg} out of 5` : 'No ratings yet'}>★ {avg ?? 'New'}</span>
        {avg != null && <> · <a href="#reviews">{count} review{count === 1 ? '' : 's'}</a></>}
        {' · '}{listing.address}, {listing.city}, {listing.state} {listing.zip}
      </p>
      {!available && av.reason && <p role="status" className="alert">{av.reason}</p>}

      {shown.length > 0 && (
        <div className={`detail-photos count-${shown.length}`}>
          {shown.map((p, i) => <img key={i} src={p} alt={`${listing.title} photo ${i + 1}`} loading={i ? 'lazy' : 'eager'} />)}
        </div>
      )}
      {!!listing.videos?.length && (
        <div className="detail-videos">
          {listing.videos.map((v, i) => <video key={i} src={v} controls preload="metadata" aria-label={`${listing.title} video ${i + 1}`} />)}
        </div>
      )}
      {!photos.length && !listing.videos?.length && <p><em>No photos or videos yet.</em></p>}

      <div className="detail-layout">
        <div className="detail-main">
          <h3>{listing.bedrooms} bed · {listing.bathrooms} bath · up to {listing.max_guests} guests</h3>
          <p className="card-meta">
            <span className={`badge ${available ? 'badge-success' : 'badge-danger'}`}>
              {available ? (requested ? 'Available for your dates' : 'Available to book') : 'Unavailable'}
            </span>
            {' '}Booked today: {listing.booked_today ?? 0}
          </p>
          {(listing.check_in_time || listing.operating_start_time) && (
            <p className="card-meta">Check-in {listing.check_in_time || '—'} · Check-out {listing.check_out_time || '—'} · Hours {listing.operating_start_time || '—'}–{listing.operating_end_time || '—'}</p>
          )}
          {listing.available_times && <p className="card-meta">{listing.available_times}</p>}

          <hr />
          <h3>About this place</h3>
          <p>{listing.description}</p>

          <hr />
          <h3>What this place offers</h3>
          {listing.amenities?.length ? <ul className="amenity-list">{listing.amenities.map(a => <li key={a}>{a}</li>)}</ul> : <p>None listed.</p>}

          <hr />
          <h3>Where you will be</h3>
          <MapView listings={[listing]} selectedId={listing.id} />
        </div>

        <aside className="detail-aside" aria-label="Reserve">
          <p className="detail-price"><strong>{money(listing.price_per_night)}</strong> <span>night</span>
            {listing.total_cost != null && <span className="listing-total"> · {money(listing.total_cost)} total for {listing.nights} night{listing.nights === 1 ? '' : 's'}</span>}
          </p>
          {auth?.user?.role === 'HOST'
            ? (
              <div className="host-preview">
                <p><strong>Guest view</strong></p>
                <p className="card-meta">{listing.status && listing.status !== 'APPROVED' ? 'Not visible to guests until it is approved.' : 'This is how guests see your listing.'}</p>
                <Link to="/host" className="btn btn-secondary btn-sm">Back to my listings</Link>
              </div>
            )
            : available
            ? <BookingForm auth={auth} listingId={id} />
            : <button type="button" className="btn" disabled aria-disabled="true">Unavailable for these dates</button>}
        </aside>
      </div>

      <hr />
      <h3 id="reviews">{avg != null ? `★ ${avg} · ${count} review${count === 1 ? '' : 's'}` : 'Reviews'}</h3>
      {list.length
        ? <ul className="review-grid">{list.map((r, i) => (
          <li key={r.id} style={{ '--i': i }}>
            <div className="review-head">
              <span className="avatar" aria-hidden="true">{(r.reviewer || 'G')[0]}</span>
              <div><strong>{r.reviewer || 'Guest'}</strong><br /><span className="card-meta" aria-label={`${r.rating} out of 5 stars`}>{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</span></div>
            </div>
            <p>{r.comment}</p>
          </li>))}</ul>
        : <p>No reviews yet.</p>}
    </section>
  );
}
