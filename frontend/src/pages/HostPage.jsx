// Frontend — Owner: Vinayak Gupta (team lead) — host listing CRUD is part of Find a Stay
// (listings are Vinayak's feature; Manoj owns booking, not listing creation).
// New listings start PENDING_APPROVAL; only the owner can edit/delete (API enforces).
import React, { useEffect, useState } from 'react';
import { api } from '../api/client.js';
// Sprint 1-2 (Manoj/Vinayak): host listing CRUD. Only the owner can edit/
// delete (API enforces 403); new listings start PENDING_APPROVAL.
const empty = { title: '', description: '', address: '', city: 'San Jose', state: 'CA', zip: '95110', lat: 37.33, lng: -121.88, price_per_night: 150, max_guests: 4, bedrooms: 2, bathrooms: 1, amenities: '', photos: '' };
export default function HostPage({ auth }) {
  const [listings, setListings] = useState([]); const [form, setForm] = useState(empty); const [editing, setEditing] = useState(null);
  const [msg, setMsg] = useState(''); const [error, setError] = useState('');
  function load() { if (auth) api.hostListings(auth.token).then(setListings).catch(e => setError(e.message)); }
  useEffect(load, [auth]);
  if (!auth) return <p>Log in as a Host to manage listings.</p>;
  if (auth.user.role !== 'HOST') return <p>Host page — only HOST accounts can manage listings (API enforces this too).</p>;
  async function submit(e) {
    e.preventDefault(); setError(''); setMsg('');
    const body = { ...form, lat: Number(form.lat), lng: Number(form.lng), price_per_night: Number(form.price_per_night), max_guests: Number(form.max_guests), bedrooms: Number(form.bedrooms), bathrooms: Number(form.bathrooms), amenities: form.amenities.split(',').map(s => s.trim()).filter(Boolean), photos: form.photos.split(',').map(s => s.trim()).filter(Boolean) };
    try {
      if (editing) { await api.updateListing(auth.token, editing, body); setMsg('Listing updated.'); }
      else { const r = await api.createListing(auth.token, body); setMsg(`Listing created (#${r.id}) — PENDING_APPROVAL until an admin approves it.`); }
      setForm(empty); setEditing(null); load();
    } catch (err) { setError(err.message); }
  }
  function edit(l) { setEditing(l.id); setForm({ ...empty, ...l, amenities: (l.amenities || []).join(', '), photos: (l.photos || []).join(', ') }); }
  async function remove(id) { try { await api.deleteListing(auth.token, id); setMsg('Listing removed (REMOVED).'); load(); } catch (err) { setError(err.message); } }
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <section>
      <h2>My listings</h2>
      {listings.map(l => <article className="page-card">
        <strong>{l.title}</strong> — {l.city} {l.zip} — ${l.price_per_night}/night — status: {l.status}{' '}
        <button onClick={() => edit(l)}>Edit</button>{' '}<button onClick={() => remove(l.id)}>Remove</button>
      </article>)}
      <h3>{editing ? `Edit listing #${editing}` : 'Add a listing'}</h3>
      <form onSubmit={submit}>
        <label>Title <input required value={form.title} onChange={e => set('title', e.target.value)} /></label><br />
        <label>Description <input required value={form.description} onChange={e => set('description', e.target.value)} /></label><br />
        <label>Address <input required value={form.address} onChange={e => set('address', e.target.value)} /></label>{' '}
        <label>City <input required value={form.city} onChange={e => set('city', e.target.value)} /></label>{' '}
        <label>State <input required value={form.state} onChange={e => set('state', e.target.value)} /></label>{' '}
        <label>Zip <input required value={form.zip} onChange={e => set('zip', e.target.value)} /></label><br />
        <label>Lat <input type="number" step="any" value={form.lat} onChange={e => set('lat', e.target.value)} /></label>{' '}
        <label>Lng <input type="number" step="any" value={form.lng} onChange={e => set('lng', e.target.value)} /></label>{' '}
        <label>Price/night <input type="number" value={form.price_per_night} onChange={e => set('price_per_night', e.target.value)} /></label>{' '}
        <label>Max guests <input type="number" value={form.max_guests} onChange={e => set('max_guests', e.target.value)} /></label>{' '}
        <label>Bedrooms <input type="number" value={form.bedrooms} onChange={e => set('bedrooms', e.target.value)} /></label>{' '}
        <label>Bathrooms <input type="number" value={form.bathrooms} onChange={e => set('bathrooms', e.target.value)} /></label><br />
        <label>Amenities (comma-separated) <input value={form.amenities} onChange={e => set('amenities', e.target.value)} /></label><br />
        <label>Photo URLs (comma-separated) <input value={form.photos} onChange={e => set('photos', e.target.value)} /></label><br />
        <button type="submit">{editing ? 'Save' : 'Create listing'}</button>{' '}
        {editing && <button type="button" onClick={() => { setEditing(null); setForm(empty); }}>Cancel edit</button>}
      </form>
      {msg && <p>{msg}</p>}{error && <p role="alert">{error}</p>}
    </section>
  );
}
