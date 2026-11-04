import React from 'react';
// Week 1: placeholder map. Sprint 2 wires Google Maps JS API here:
// address search -> geocode -> pins for search results -> click pin -> listing.
// Leaflet with seed lat/lng is the fallback if the Maps key/quota blocks.
export default function MapView({ listings }) {
  return (
    <div style={{ border: '1px dashed #999', padding: 12, margin: '12px 0' }}>
      <strong>Map view (Week 1 placeholder)</strong>
      <ul>{listings.slice(0, 5).map(l => <li key={l.id}>{l.title} — {l.lat}, {l.lng}</li>)}</ul>
      <p><small>Google Maps integration lands in Sprint 2 (US11/US13). See docs/wireframes.md screen 3.</small></p>
    </div>
  );
}
