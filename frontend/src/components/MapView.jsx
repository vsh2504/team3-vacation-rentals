// Frontend — Owner: Vinayak Gupta (team lead)
// Feature: Find a Stay — map view (OSM embed / Google Maps embed, pins = results).
import React from 'react';
import { Link } from 'react-router-dom';
// Sprint 2 map: no JS SDK needed, so no API key is required to demo.
// If VITE_GOOGLE_MAPS_KEY is set, embed Google Maps; otherwise embed
// OpenStreetMap centred on the first result. Pins = search results;
// clicking a pin opens the listing. Address search is a text filter on
// address/city/zip in SearchPage — full geocoding needs a Maps key
// (see docs/wireframes.md screen 3, and RUNNING.md).
export default function MapView({ listings }) {
  if (!listings.length) return <p>No listings to show on the map.</p>;
  const first = listings[0];
  const key = import.meta.env.VITE_GOOGLE_MAPS_KEY;
  const src = key
    ? `https://www.google.com/maps/embed/v1/view?key=${key}&center=${first.lat},${first.lng}&zoom=12`
    : `https://www.openstreetmap.org/export/embed.html?bbox=${first.lng - 0.08},${first.lat - 0.05},${first.lng + 0.08},${first.lat + 0.05}&layer=mapnik&marker=${first.lat},${first.lng}`;
  return (
    <div style={{ border: '1px solid #ddd', padding: 12, margin: '12px 0' }}>
      <strong>Map — {key ? 'Google Maps' : 'OpenStreetMap (no key needed)'} — pins = search results</strong>
      <iframe title="map" src={src} width="100%" height="280" style={{ border: 0, marginTop: 8 }} loading="lazy" />
      <ul>{listings.map(l => (
        <li key={l.id}><Link to={`/listings/${l.id}`}>📍 {l.title}</Link> — {l.lat}, {l.lng} — {l.city} {l.zip}</li>
      ))}</ul>
    </div>
  );
}
