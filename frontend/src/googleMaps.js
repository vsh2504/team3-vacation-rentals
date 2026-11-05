// Lazy loader for the Google Maps JS API using the modern importLibrary loader
// (compatible with the Maps Demo Key). Resolves to `google` once the maps, marker
// and places libraries are ready, or null when no key / load failure.
const KEY = import.meta.env.VITE_GOOGLE_MAPS_KEY;
let promise = null;

export const hasGoogleMaps = Boolean(KEY);

function injectScript() {
  return new Promise((resolve, reject) => {
    if (window.google?.maps?.importLibrary) return resolve();
    const s = document.createElement('script');
    s.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(KEY)}&v=weekly&loading=async`;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('Google Maps script failed to load'));
    document.head.appendChild(s);
  });
}

export function loadGoogleMaps() {
  if (!KEY) return Promise.resolve(null);
  if (!promise) {
    promise = injectScript()
      .then(() => Promise.all([
        window.google.maps.importLibrary('maps'),
        window.google.maps.importLibrary('marker'),
        window.google.maps.importLibrary('places'),
      ]))
      .then(() => window.google)
      .catch(() => { promise = null; return null; });
  }
  return promise;
}
