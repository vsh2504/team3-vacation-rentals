// Frontend — Owner: Vinayak Gupta (team lead)
// Feature: Find a Stay — listing card used by search results.
import React from 'react';
import { Link } from 'react-router-dom';
// Props are the listing contract from docs/contracts.md.
export default function ListingCard({ listing }) {
  return (
    <article style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12, margin: '12px 0' }}>
      {listing.photos?.[0] && <img src={listing.photos[0]} alt={listing.title} style={{ width: '100%', maxHeight: 180, objectFit: 'cover', borderRadius: 6 }} />}
      <h3><Link to={`/listings/${listing.id}`}>{listing.title}</Link></h3>
      <p>{listing.city}, {listing.state} {listing.zip} — ${listing.price_per_night}/night — up to {listing.max_guests} guests — {listing.bedrooms} bed, {listing.bathrooms} bath</p>
      <p>Amenities: {(listing.amenities || []).join(', ')}</p>
      <p># booked today: {listing.booked_today ?? '—'} {listing.status ? `— status: ${listing.status}` : ''}</p>
    </article>
  );
}
