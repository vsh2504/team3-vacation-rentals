// Frontend — Owner: Vinayak Gupta (team lead)
// Feature: Find a Stay — listing card used by search results.
import React from 'react';
import { Link } from 'react-router-dom';

const money = v => (v == null ? null : `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`);

export default function ListingCard({ listing, index, selected, onSelect, search = '' }) {
  const l = listing;
  const requested = l.availability?.requested;
  const available = l.available ?? l.is_available ?? true;
  const href = `/listings/${l.id}${search}`;
  const reviews = l.reviews || [];
  return (
    <article className="card" aria-labelledby={`card-${l.id}`}
      style={selected ? { outline: '3px solid var(--sn-color-accent, #f2b134)' } : undefined}>
      {l.photos?.[0]
        ? <img src={l.photos[0]} alt={`${l.title} photo`} loading="lazy" />
        : l.videos?.[0]
          ? <video src={l.videos[0]} controls preload="none" aria-label={`${l.title} video`} style={{ width: '100%', maxHeight: 200 }} />
          : <div className="card-meta" style={{ padding: 16 }}>No media yet</div>}
      <div className="card-body">
        <h3 className="card-title" id={`card-${l.id}`}>
          {index != null && <span aria-hidden="true">{index + 1}. </span>}
          <Link to={href}>{l.title}</Link>
        </h3>
        <p className="card-meta">{l.city}, {l.state} {l.zip} — up to {l.max_guests} guests — {l.bedrooms} bed, {l.bathrooms} bath</p>
        <p className="card-meta">
          {l.average_rating != null ? <>★ {l.average_rating} ({l.review_count ?? reviews.length} reviews)</> : 'No reviews yet'}
          {' · '}Booked today: {l.booked_today ?? 0}
        </p>
        {!!l.amenities?.length && <p className="card-meta">Amenities: {l.amenities.join(', ')}</p>}
        {reviews[0] && <p className="card-meta"><em>“{reviews[0].comment}”</em></p>}
        <p className="card-price">{money(l.price_per_night)} <span>night</span>
          {l.total_cost != null && <span> · {money(l.total_cost)} total for {l.nights} night{l.nights === 1 ? '' : 's'}</span>}
        </p>
        <p>
          <span className={`badge ${available ? 'badge-success' : 'badge-danger'}`}>
            {available ? (requested ? 'Available for your dates' : 'Approved') : 'Unavailable'}
          </span>
          {!available && l.availability?.reason && <span className="card-meta"> {l.availability.reason}</span>}
        </p>
        <p style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {onSelect && <button type="button" className="btn btn-ghost btn-sm" onClick={() => onSelect(l.id)} aria-pressed={!!selected}>Show on map</button>}
          {available
            ? <Link className="btn btn-primary btn-sm" to={href}>{requested ? 'Book' : 'View & book'}</Link>
            : <button type="button" className="btn btn-sm" disabled aria-disabled="true">Unavailable</button>}
        </p>
      </div>
    </article>
  );
}
