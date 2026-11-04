import React from 'react';
// Props are the listing contract from docs/contracts.md — do not add
// fields here without adding them to the API DTO first.
export default function ListingCard({ listing, role }) {
  return (
    <article style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12, margin: '12px 0' }}>
      <h3>{listing.title}</h3>
      <p>{listing.city}, {listing.state} {listing.zip} — ${listing.price_per_night}/night — up to {listing.max_guests} guests</p>
      <p>Amenities: {listing.amenities.join(', ')}</p>
      <p># booked today: (API field, Sprint 2) — Book button below is enabled only when available for the requested dates.</p>
      {role === 'CUSTOMER' && <button>Book</button>}
      {role === 'HOST' && <button>Edit my listing</button>}
    </article>
  );
}
