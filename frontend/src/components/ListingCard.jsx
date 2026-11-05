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
  const rating = l.average_rating != null ? Number(l.average_rating) : null;
  const reviewCount = l.review_count ?? reviews.length;
  return (
    <article className={`card listing-card${selected ? ' is-selected' : ''}`} aria-labelledby={`card-${l.id}`} style={{ '--i': index ?? 0 }}>
      <div className="listing-media">
        {l.photos?.[0]
          ? <img src={l.photos[0]} alt={`${l.title} photo`} loading="lazy" />
          : l.videos?.[0]
            ? <video src={l.videos[0]} controls preload="none" aria-label={`${l.title} video`} />
            : <div className="listing-media-empty">No photos yet</div>}
        {requested && (
          <span className={`listing-chip ${available ? 'is-ok' : 'is-off'}`}>{available ? 'Available for your dates' : 'Unavailable'}</span>
        )}
      </div>
      <div className="card-body">
        <div className="listing-row">
          <h3 className="card-title" id={`card-${l.id}`}><Link to={href}>{l.title}</Link></h3>
          <span className="listing-rating" aria-label={rating != null ? `Rated ${rating} out of 5 from ${reviewCount} reviews` : 'No reviews yet'}>
            {rating != null ? <>★ {rating} <span>({reviewCount})</span></> : <span>New</span>}
          </span>
        </div>
        <p className="card-meta">{l.city}, {l.state} · up to {l.max_guests} guests</p>
        <p className="card-meta">{l.bedrooms} bed · {l.bathrooms} bath{(l.booked_today ?? 0) > 0 ? ` · booked ${l.booked_today}× today` : ''}</p>
        <p className="card-price"><strong>{money(l.price_per_night)}</strong> <span>night</span>
          {l.total_cost != null && <span className="listing-total"> · {money(l.total_cost)} total for {l.nights} night{l.nights === 1 ? '' : 's'}</span>}
        </p>
        {!available && l.availability?.reason && <p className="card-meta">{l.availability.reason}</p>}
        {(onSelect || !available) && (
          <p className="card-actions">
            {onSelect && <button type="button" className="btn btn-ghost btn-sm" onClick={() => onSelect(l.id)} aria-pressed={!!selected}>Show on map</button>}
            {!available && <button type="button" className="btn btn-sm" disabled aria-disabled="true">Unavailable</button>}
          </p>
        )}
      </div>
    </article>
  );
}
