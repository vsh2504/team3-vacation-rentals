// Frontend — Owner: Vinayak Gupta (team lead)
// Feature: Find a Stay — OpenStreetMap view with one distinct marker per result.
// Dependency-free slippy map: OSM raster tiles + positioned marker buttons.
import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';

const W = 768, H = 420, T = 256;
const worldX = (lng, z) => ((lng + 180) / 360) * T * 2 ** z;
const worldY = (lat, z) => {
  const r = (lat * Math.PI) / 180;
  return ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * T * 2 ** z;
};

function frame(points) {
  if (!points.length) return { z: 2, cx: 0, cy: 0 };
  const lats = points.map(p => p.lat), lngs = points.map(p => p.lng);
  let z = 16;
  for (; z > 1; z--) {
    const w = worldX(Math.max(...lngs), z) - worldX(Math.min(...lngs), z);
    const h = worldY(Math.min(...lats), z) - worldY(Math.max(...lats), z);
    if (w < W - 120 && h < H - 120) break;
  }
  z = Math.min(z, 15);
  return {
    z,
    cx: (worldX(Math.min(...lngs), z) + worldX(Math.max(...lngs), z)) / 2,
    cy: (worldY(Math.min(...lats), z) + worldY(Math.max(...lats), z)) / 2,
  };
}

export default function MapView({ listings, selectedId, onSelect }) {
  const items = (listings || []).filter(l => Number.isFinite(Number(l.lat)) && Number.isFinite(Number(l.lng)))
    .map(l => ({ ...l, lat: Number(l.lat), lng: Number(l.lng) }));
  const { z, cx, cy } = useMemo(() => frame(items), [items.map(i => `${i.id}:${i.lat}:${i.lng}`).join('|')]);
  const selected = items.find(l => l.id === selectedId);

  if (!items.length) return <div className="map-box" role="status">No mapped listings to show.</div>;

  const ox = cx - W / 2, oy = cy - H / 2, n = 2 ** z;
  const tiles = [];
  for (let tx = Math.floor(ox / T); tx <= Math.floor((ox + W) / T); tx++) {
    for (let ty = Math.floor(oy / T); ty <= Math.floor((oy + H) / T); ty++) {
      if (ty < 0 || ty >= n) continue;
      const wx = ((tx % n) + n) % n;
      tiles.push(
        <img key={`${tx}/${ty}`} alt="" aria-hidden="true" draggable="false"
          src={`https://tile.openstreetmap.org/${z}/${wx}/${ty}.png`}
          style={{ position: 'absolute', left: `${((tx * T - ox) / W) * 100}%`, top: `${((ty * T - oy) / H) * 100}%`,
            width: `${(T / W) * 100}%`, height: `${(T / H) * 100}%`, borderRadius: 0 }} />
      );
    }
  }

  return (
    <div className="map-box">
      <div role="group" aria-label={`Map of ${items.length} listings on OpenStreetMap`}
        style={{ position: 'relative', width: '100%', aspectRatio: `${W} / ${H}`, overflow: 'hidden', background: '#e8e4da', borderRadius: 8 }}>
        {tiles}
        {items.map((l, i) => {
          const active = l.id === selectedId;
          return (
            <button key={l.id} type="button" onClick={() => onSelect?.(l.id)}
              aria-pressed={active} aria-label={`Marker ${i + 1}: ${l.title}, $${l.price_per_night} per night`}
              style={{ position: 'absolute', left: `${((worldX(l.lng, z) - ox) / W) * 100}%`, top: `${((worldY(l.lat, z) - oy) / H) * 100}%`,
                transform: 'translate(-50%, -100%)', zIndex: active ? 3 : 2, minWidth: 32, minHeight: 32, padding: '2px 8px',
                borderRadius: 16, border: '2px solid #fff', cursor: 'pointer', fontWeight: 700, fontSize: 13,
                background: active ? '#f2b134' : '#0b6169', color: active ? '#12272d' : '#fff', boxShadow: '0 1px 4px rgba(0,0,0,.4)' }}>
              {i + 1}
            </button>
          );
        })}
        <span style={{ position: 'absolute', right: 0, bottom: 0, background: 'rgba(255,255,255,.85)', fontSize: 11, padding: '1px 6px' }}>
          © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors
        </span>
      </div>
      <div aria-live="polite" className="card-meta" style={{ marginTop: 8 }}>
        {selected ? (
          <>
            <strong>{items.indexOf(selected) + 1}. {selected.title}</strong> — {selected.address}, {selected.city} ({selected.lat.toFixed(4)}, {selected.lng.toFixed(4)}){' '}
            <Link to={selected.listing_url || `/listings/${selected.id}`}>View listing</Link>{' · '}
            <a href={selected.map_url || `https://www.openstreetmap.org/?mlat=${selected.lat}&mlon=${selected.lng}#map=16/${selected.lat}/${selected.lng}`} target="_blank" rel="noreferrer">Open in OpenStreetMap</a>
          </>
        ) : 'Select a marker or result to see its location.'}
      </div>
    </div>
  );
}
