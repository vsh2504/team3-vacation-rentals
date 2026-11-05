// Frontend — Owner: Vinayak Gupta (team lead)
// Feature: Find a Stay — Google Maps view with one numbered marker per result.
// Without a key (or if Google fails to load) a plain list with Google Maps links is shown.
import React, { useEffect, useRef, useState } from 'react';
import { hasGoogleMaps, loadGoogleMaps } from '../googleMaps.js';
import { Link } from 'react-router-dom';

const gmapsLink = (l) => `https://www.google.com/maps/search/?api=1&query=${l.lat},${l.lng}`;

function MapCaption({ items, selected }) {
  const mapHref = selected && gmapsLink(selected);
  return (
    <div aria-live="polite" className="card-meta" style={{ marginTop: 8 }}>
      {selected ? (
        <>
          <strong>{items.indexOf(selected) + 1}. {selected.title}</strong> — {selected.address}, {selected.city} ({selected.lat.toFixed(4)}, {selected.lng.toFixed(4)}){' '}
          {selected.id !== 0 && <><Link to={selected.listing_url || `/listings/${selected.id}`}>View listing</Link>{' · '}</>}
          <a href={mapHref} target="_blank" rel="noreferrer">Open in Google Maps</a>
        </>
      ) : 'Select a marker or result to see its location.'}
    </div>
  );
}

function GoogleMapView({ items, selectedId, onSelect, onFail }) {
  const ref = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadGoogleMaps().then(async (g) => {
      if (cancelled) return;
      if (!g) { onFail(); return; }
      try {
        mapRef.current = new g.maps.Map(ref.current, { center: { lat: 37.3, lng: -121.9 }, zoom: 10, mapTypeControl: false, streetViewControl: false });
        setReady(true);
      } catch { onFail(); }
    });
    return () => { cancelled = true; };
  }, []); // eslint-disable-line

  useEffect(() => {
    if (!ready) return;
    const g = window.google, map = mapRef.current;
    markersRef.current.forEach(m => m.setMap(null));
    const bounds = new g.maps.LatLngBounds();
    markersRef.current = items.map((l, i) => {
      const pos = { lat: l.lat, lng: l.lng };
      bounds.extend(pos);
      const active = l.id === selectedId;
      const m = new g.maps.Marker({ position: pos, map, title: l.title, zIndex: active ? 10 : 1,
        label: { text: String(i + 1), color: active ? '#12272d' : '#fff', fontWeight: '700' },
        icon: { path: g.maps.SymbolPath.CIRCLE, scale: 14, fillColor: active ? '#f2b134' : '#0b6169', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2 } });
      m.addListener('click', () => onSelect?.(l.id));
      return m;
    });
    if (items.length === 1) { map.setCenter({ lat: items[0].lat, lng: items[0].lng }); map.setZoom(14); }
    else if (items.length) map.fitBounds(bounds, 48);
  }, [ready, items.map(i => `${i.id}:${i.lat}:${i.lng}`).join('|'), selectedId]); // eslint-disable-line

  return <div ref={ref} role="group" aria-label={`Google map of ${items.length} listings`} style={{ width: '100%', height: 420, borderRadius: 8 }} />;
}

export default function MapView({ listings, selectedId, onSelect }) {
  const [gFailed, setGFailed] = useState(false);
  const useGoogle = hasGoogleMaps && !gFailed;
  const items = (listings || []).filter(l => Number.isFinite(Number(l.lat)) && Number.isFinite(Number(l.lng)))
    .map(l => ({ ...l, lat: Number(l.lat), lng: Number(l.lng) }));
  const selected = items.find(l => l.id === selectedId);

  if (!items.length) return <div className="map-box" role="status">No mapped listings to show.</div>;

  if (useGoogle) {
    return (
      <div className="map-box">
        <GoogleMapView items={items} selectedId={selectedId} onSelect={onSelect} onFail={() => setGFailed(true)} />
        <MapCaption items={items} selected={selected} />
      </div>
    );
  }

  return (
    <div className="map-box" role="group" aria-label="Listing locations">
      <p className="card-meta" role="status">
        {hasGoogleMaps ? 'Google Maps could not be loaded.' : 'Google Maps is not configured (set VITE_GOOGLE_MAPS_KEY).'} Locations:
      </p>
      <ol style={{ margin: 0, paddingLeft: '1.25rem' }}>
        {items.map(l => (
          <li key={l.id}>
            <strong>{l.title}</strong>{l.address ? ` — ${l.address}, ${l.city}` : ''}{' '}
            <a href={gmapsLink(l)} target="_blank" rel="noreferrer">Open in Google Maps</a>
          </li>
        ))}
      </ol>
    </div>
  );
}
