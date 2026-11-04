// Frontend — Owner: Vinayak Gupta (team lead)
// Feature: Find a Stay — listing card used by search results.
import React from 'react';
import { Link } from 'react-router-dom';
// Props are the listing contract from docs/contracts.md.
export default function ListingCard({ listing }) {
  return (
    <article className="card">
      {listing.photos?.[0] && <img src={listing.photos[0]} alt={listing.title} />}
      <div className="card-body">
        <h3 className="card-title"><Link to={`/listings/${listing.id}`}>{listing.title}</Link></h3>
        <p className="card-meta">{listing.city}, {listing.state} {listing.zip} — up to {listing.max_guests} guests — {listing.bedrooms} bed, {listing.bathrooms} bath</p>
        <p className="card-meta">Amenities: {(listing.amenities || []).join(', ')}</p>
        <p className="card-meta"># booked today: {listing.booked_today ?? '—'}{listing.status ? ` — ${listing.status}` : ''}</p>
        <p className="card-price">${listing.price_per_night} <span>night</span></p>
      </div>
    </article>
  );
}
