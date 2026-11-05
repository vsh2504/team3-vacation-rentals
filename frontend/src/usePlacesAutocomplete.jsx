// Address / city suggestions using the NEW Places API (AutocompleteSuggestion + Place),
// which the Maps Demo Key supports. No-op without a Maps key, so forms keep their
// plain-text + geocode fallback.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { hasGoogleMaps, loadGoogleMaps } from './googleMaps.js';

// Flatten a new-API Place into the fields our forms use.
export function parsePlace(place) {
  const comps = place.addressComponents || [];
  const get = (t, short) => {
    const c = comps.find((x) => x.types.includes(t));
    return c ? (short ? c.shortText : c.longText) : undefined;
  };
  const loc = place.location;
  return {
    formatted: place.formattedAddress || '',
    street: [get('street_number'), get('route')].filter(Boolean).join(' '),
    city: get('locality') || get('sublocality') || get('postal_town'),
    state: get('administrative_area_level_1', true),
    zip: get('postal_code'),
    lat: loc ? loc.lat() : undefined,
    lng: loc ? loc.lng() : undefined,
  };
}

// opts.types: Places "primary types", e.g. ['locality'] for city search.
export function usePlacesAutocomplete(onPick, opts = {}) {
  const [items, setItems] = useState([]);
  const timer = useRef(null);
  const lib = useRef(null);
  const token = useRef(null);
  const seq = useRef(0);
  const cb = useRef(onPick);
  cb.current = onPick;
  const types = useRef(opts.types);

  // Call from the input's onChange with the new text.
  const query = useCallback((text) => {
    clearTimeout(timer.current);
    if (!hasGoogleMaps || String(text).trim().length < 3) { seq.current++; setItems([]); return; }
    timer.current = setTimeout(async () => {
      const my = ++seq.current;
      try {
        const g = await loadGoogleMaps();
        if (!g) return;
        lib.current = lib.current || await g.maps.importLibrary('places');
        token.current = token.current || new lib.current.AutocompleteSessionToken();
        const { suggestions } = await lib.current.AutocompleteSuggestion.fetchAutocompleteSuggestions({
          input: text,
          sessionToken: token.current,
          includedRegionCodes: ['us'],
          ...(types.current ? { includedPrimaryTypes: types.current } : {}),
        });
        if (my === seq.current) setItems(suggestions.map((s) => s.placePrediction).filter(Boolean));
      } catch {
        if (my === seq.current) setItems([]);
      }
    }, 250);
  }, []);

  const select = useCallback(async (prediction) => {
    seq.current++;
    setItems([]);
    try {
      const place = prediction.toPlace();
      await place.fetchFields({ fields: ['formattedAddress', 'addressComponents', 'location'] });
      token.current = null; // session ends on selection
      cb.current(parsePlace(place));
    } catch { /* leave the typed text as-is */ }
  }, []);

  const close = useCallback(() => { seq.current++; setItems([]); }, []);
  useEffect(() => () => clearTimeout(timer.current), []);
  return { items, query, select, close };
}

export function PlaceSuggestions({ ac, label = 'Google Maps suggestions' }) {
  if (!ac.items.length) return null;
  return (
    <ul role="listbox" aria-label={label}
      style={{ position: 'absolute', top: '100%', left: 0, right: 0, minWidth: 260, zIndex: 50, listStyle: 'none', margin: '4px 0 0', padding: 4, border: '1px solid var(--sn-line)', borderRadius: 12, background: 'var(--sn-surface)', boxShadow: '0 12px 28px rgba(0,0,0,.35)' }}>
      {ac.items.map((p, i) => (
        <li key={i} role="option" aria-selected="false">
          <button type="button" className="btn btn-ghost btn-sm" style={{ width: '100%', justifyContent: 'flex-start', textAlign: 'left' }}
            onClick={() => ac.select(p)}>
            📍 {p.text?.toString?.() || ''}
          </button>
        </li>
      ))}
      <li aria-hidden="true" className="card-meta" style={{ textAlign: 'right', padding: '2px 8px' }}>powered by Google</li>
    </ul>
  );
}
