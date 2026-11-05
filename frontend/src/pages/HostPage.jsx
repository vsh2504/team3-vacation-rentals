// Frontend — Owner: Vinayak Gupta / Host Experience
// Feature: Host Listing Management — property listing CRUD and inventory dashboard.
// Captures identity, contact info, address geocoding, coordinates, operating hours,
// available booking times, capacity, amenities, photos, and videos.
// Displays moderation status, completeness score, edit, and removal workflows (Requirements 4.1-4.4, 8.2-8.4).
import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import MapView from '../components/MapView.jsx';
import { hasGoogleMaps } from '../googleMaps.js';
import { PlaceSuggestions, usePlacesAutocomplete } from '../usePlacesAutocomplete.jsx';
import { Alert, Badge, Button, Card, Spinner } from '../components/ui/index.js';

const POPULAR_AMENITIES = [
  'WiFi',
  'Kitchen',
  'Parking',
  'Washer',
  'Dryer',
  'Pool',
  'Hot tub',
  'Air conditioning',
  'Dedicated workspace',
  'Pet friendly',
  'Balcony',
  'Gym',
  'TV',
  'Fireplace',
];

const INITIAL_FORM = {
  title: '',
  description: '',
  // Contact info
  host_contact_name: '',
  host_contact_email: '',
  host_contact_phone: '',
  // Location
  address: '',
  city: 'San Jose',
  state: 'CA',
  zip: '95110',
  lat: 37.3382,
  lng: -121.8863,
  // Hours & Schedule
  operating_start_time: '08:00',
  operating_end_time: '22:00',
  check_in_time: '15:00',
  check_out_time: '11:00',
  available_times: 'Check-in 3pm, check-out 11am; available year-round unless booked',
  // Capacity & Pricing
  price_per_night: 150,
  max_guests: 4,
  bedrooms: 2,
  bathrooms: 1,
  // Amenities & Media
  amenities: ['WiFi', 'Kitchen', 'Parking'],
  customAmenities: '',
  photos: '',
  videos: '',
};

export default function HostPage({ auth }) {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(INITIAL_FORM);
  const [editingId, setEditingId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLookingUp, setIsLookingUp] = useState(false);
  const [lookupMsg, setLookupMsg] = useState(null);
  const [actionMsg, setActionMsg] = useState('');
  // Google address suggestions: fills street, city, state, ZIP and coordinates in one pick.
  const addressAC = usePlacesAutocomplete((p) => {
    setForm((prev) => ({
      ...prev,
      address: p.street || p.formatted.split(',')[0] || prev.address,
      city: p.city || prev.city,
      state: p.state ? p.state.slice(0, 2).toUpperCase() : prev.state,
      zip: p.zip || prev.zip,
      lat: p.lat != null ? Number(p.lat.toFixed(6)) : prev.lat,
      lng: p.lng != null ? Number(p.lng.toFixed(6)) : prev.lng,
    }));
    setLookupMsg({ type: 'success', text: `Address selected from Google Maps: ${p.formatted}. City, ZIP and coordinates were filled in.` });
  });
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState(null);
  const [error, setError] = useState('');
  const [removeConfirmId, setRemoveConfirmId] = useState(null);
  const [expandedCompletenessId, setExpandedCompletenessId] = useState(null);

  const formSectionRef = useRef(null);

  function loadListings() {
    if (!auth) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');
    api.hostListings(auth.token)
      .then((data) => {
        setListings(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load your listings.');
      })
      .finally(() => {
        setLoading(false);
      });
  }

  useEffect(() => {
    loadListings();
  }, [auth]); // eslint-disable-line

  if (!auth) {
    return (
      <section aria-labelledby="host-heading">
        <h2 id="host-heading">Host Portal</h2>
        <Card>
          <div className="empty-state" style={{ margin: 0 }}>
            <h3>Host sign-in required</h3>
            <p style={{ marginBottom: '1rem' }}>
              Sign in with your host account to manage your listings.
            </p>
            <Link to="/auth" className="btn btn-primary">
              Sign In as Host
            </Link>
          </div>
        </Card>
      </section>
    );
  }

  if (auth.user?.role !== 'HOST') {
    return (
      <section aria-labelledby="host-heading">
        <h2 id="host-heading">Host Portal</h2>
        <Alert variant="warning" title="Restricted access">
          You are currently signed in as <strong>{auth.user?.role}</strong> ({auth.user?.email}).
          Only Host accounts can create and manage property listings. Please register or sign in as a Host to continue.
        </Alert>
      </section>
    );
  }

  // Completeness evaluator (Requirement: show completeness on each owned listing)
  function evaluateCompleteness(l) {
    const checks = [
      { id: 'identity', label: 'Title & description', ok: !!(l.title?.trim() && l.description?.trim()) },
      { id: 'address', label: 'Full street address & ZIP', ok: !!(l.address?.trim() && l.city?.trim() && l.state?.trim() && l.zip?.trim()) },
      { id: 'coords', label: 'Geocoded map coordinates', ok: l.lat != null && l.lng != null },
      { id: 'pricing', label: 'Price & guest capacity', ok: Number(l.price_per_night) > 0 && Number(l.max_guests) >= 1 },
      { id: 'contact', label: 'Host contact details', ok: !!(l.host_contact_name?.trim() || l.host_contact_email?.trim() || l.host_contact_phone?.trim()) },
      { id: 'hours', label: 'Operating hours & check-in/out', ok: !!(l.check_in_time && l.check_out_time) },
      { id: 'amenities', label: 'Amenities listed', ok: Array.isArray(l.amenities) && l.amenities.length > 0 },
      { id: 'photos', label: 'Property photos provided', ok: Array.isArray(l.photos) && l.photos.length > 0 },
    ];
    const passed = checks.filter((c) => c.ok).length;
    const score = Math.round((passed / checks.length) * 100);
    const isComplete = passed === checks.length;
    const missing = checks.filter((c) => !c.ok).map((c) => c.label);
    return { checks, passed, total: checks.length, score, isComplete, missing };
  }

  // Address geocoding helper (server picks Google when configured, else Nominatim)
  async function handleAddressLookup() {
    const queryParts = [form.address, form.city, form.state, form.zip].filter(Boolean);
    const query = queryParts.join(', ').trim();

    if (!form.address.trim()) {
      setLookupMsg({ type: 'error', text: 'Please enter a street address to look up coordinates.' });
      return;
    }

    setIsLookingUp(true);
    setLookupMsg(null);
    try {
      const res = await api.geocode(query);
      setForm((prev) => ({
        ...prev,
        lat: res.lat != null ? Number(res.lat.toFixed(6)) : prev.lat,
        lng: res.lng != null ? Number(res.lng.toFixed(6)) : prev.lng,
        city: res.city || prev.city,
        state: res.state ? res.state.slice(0, 2).toUpperCase() : prev.state,
        zip: res.zip || prev.zip,
      }));
      setLookupMsg({
        type: 'success',
        text: `Coordinates resolved: ${res.lat.toFixed(4)}, ${res.lng.toFixed(4)} via ${res.provider === 'google' ? 'Google Maps' : (res.provider || 'geocoder')}.`,
      });
    } catch (err) {
      setLookupMsg({
        type: 'error',
        text: err.message || 'Could not locate address coordinates. You may enter latitude and longitude manually.',
      });
    } finally {
      setIsLookingUp(false);
    }
  }

  function handleAmenityToggle(amenity) {
    setForm((prev) => {
      const exists = prev.amenities.includes(amenity);
      const next = exists
        ? prev.amenities.filter((a) => a !== amenity)
        : [...prev.amenities, amenity];
      return { ...prev, amenities: next };
    });
  }

  function startEdit(listing) {
    setEditingId(listing.id);
    setError('');
    setActionMsg('');
    setLookupMsg(null);

    // Split known amenities from custom ones
    const currentAmenities = listing.amenities || [];
    const known = currentAmenities.filter((a) => POPULAR_AMENITIES.includes(a));
    const custom = currentAmenities.filter((a) => !POPULAR_AMENITIES.includes(a));

    setForm({
      title: listing.title || '',
      description: listing.description || '',
      host_contact_name: listing.host_contact_name || '',
      host_contact_email: listing.host_contact_email || '',
      host_contact_phone: listing.host_contact_phone || '',
      address: listing.address || '',
      city: listing.city || 'San Jose',
      state: listing.state || 'CA',
      zip: listing.zip || '95110',
      lat: listing.lat ?? 37.3382,
      lng: listing.lng ?? -121.8863,
      operating_start_time: listing.operating_start_time || '08:00',
      operating_end_time: listing.operating_end_time || '22:00',
      check_in_time: listing.check_in_time || '15:00',
      check_out_time: listing.check_out_time || '11:00',
      available_times: listing.available_times || 'Check-in 3pm, check-out 11am; available year-round unless booked',
      price_per_night: listing.price_per_night != null ? Number(listing.price_per_night) : 150,
      max_guests: listing.max_guests || 4,
      bedrooms: listing.bedrooms != null ? listing.bedrooms : 2,
      bathrooms: listing.bathrooms != null ? listing.bathrooms : 1,
      amenities: known,
      customAmenities: custom.join(', '),
      photos: (listing.photos || []).join('\n'),
      videos: (listing.videos || []).join('\n'),
    });

    if (formSectionRef.current) {
      formSectionRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(INITIAL_FORM);
    setLookupMsg(null);
  }

  async function handleRemove(listingId) {
    setError('');
    setActionMsg('');
    try {
      await api.deleteListing(auth.token, listingId);
      setActionMsg(`Listing #${listingId} has been archived (REMOVED).`);
      setRemoveConfirmId(null);
      if (editingId === listingId) {
        cancelEdit();
      }
      loadListings();
    } catch (err) {
      setError(err.message || `Failed to remove listing #${listingId}.`);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setActionMsg('');
    setLookupMsg(null);

    // Parse custom amenities
    const extraAmenities = form.customAmenities
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    const combinedAmenities = Array.from(new Set([...form.amenities, ...extraAmenities]));

    // Parse photos and videos (support newlines or commas)
    const photoList = form.photos
      .split(/[\n,]/)
      .map((s) => s.trim())
      .filter(Boolean);
    const videoList = form.videos
      .split(/[\n,]/)
      .map((s) => s.trim())
      .filter(Boolean);

    const payload = {
      title: form.title.trim(),
      description: form.description.trim(),
      host_contact_name: form.host_contact_name.trim(),
      host_contact_email: form.host_contact_email.trim(),
      host_contact_phone: form.host_contact_phone.trim(),
      address: form.address.trim(),
      city: form.city.trim(),
      state: form.state.trim().toUpperCase(),
      zip: form.zip.trim(),
      lat: form.lat !== '' && form.lat != null ? Number(form.lat) : null,
      lng: form.lng !== '' && form.lng != null ? Number(form.lng) : null,
      operating_start_time: form.operating_start_time || '00:00',
      operating_end_time: form.operating_end_time || '23:59',
      check_in_time: form.check_in_time || '15:00',
      check_out_time: form.check_out_time || '11:00',
      available_times: form.available_times.trim() || 'Check-in 3pm, check-out 11am',
      price_per_night: Number(form.price_per_night),
      max_guests: Number(form.max_guests),
      bedrooms: Number(form.bedrooms),
      bathrooms: Number(form.bathrooms),
      amenities: combinedAmenities,
      photos: photoList,
      videos: videoList,
    };

    setIsSubmitting(true);
    try {
      if (editingId) {
        await api.updateListing(auth.token, editingId, payload);
        setActionMsg(`Listing #${editingId} updated successfully! Status set to PENDING_APPROVAL for admin moderation.`);
      } else {
        const created = await api.createListing(auth.token, payload);
        setActionMsg(`Listing created successfully (#${created.id})! Status is PENDING_APPROVAL until approved by an administrator.`);
      }
      setEditingId(null);
      setForm(INITIAL_FORM);
      loadListings();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      setError(err.message || 'Failed to save listing. Please check form fields.');
    } finally {
      setIsSubmitting(false);
    }
  }

  function getStatusBadge(status) {
    switch (status) {
      case 'APPROVED':
        return <Badge variant="success">APPROVED</Badge>;
      case 'PENDING_APPROVAL':
        return <Badge variant="warning">PENDING APPROVAL</Badge>;
      case 'REJECTED':
        return <Badge variant="danger">REJECTED</Badge>;
      case 'REMOVED':
        return <Badge variant="neutral">REMOVED</Badge>;
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  }

  // Upload chosen files and append their URLs to the photos/videos fields.
  async function handleFiles(e) {
    const files = Array.from(e.target.files || []);
    e.target.value = '';
    if (!files.length) return;
    setUploading(true);
    setUploadMsg(null);
    const photos = [], videos = [], errors = [];
    for (const file of files) {
      try {
        const out = await api.uploadMedia(auth.token, file);
        (out.kind === 'video' ? videos : photos).push(out.url);
      } catch (err) {
        errors.push(`${file.name}: ${err.message}`);
      }
    }
    const join = (cur, add) => [cur.trim(), ...add].filter(Boolean).join('\n');
    setForm((f) => ({ ...f, photos: join(f.photos, photos), videos: join(f.videos, videos) }));
    setUploading(false);
    setUploadMsg(errors.length
      ? { type: 'error', text: errors.join(' | ') }
      : { type: 'success', text: `Uploaded ${photos.length} photo(s) and ${videos.length} video(s).` });
  }

  // Parse photos for live preview in form
  const previewPhotos = form.photos
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter((s) => s.startsWith('http://') || s.startsWith('https://') || s.startsWith('/'));

  return (
    <section aria-labelledby="host-page-heading">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
        <div>
          <h2 id="host-page-heading" style={{ margin: 0 }}>Host Management Portal</h2>
        </div>
        <Button
          type="button"
          variant="primary"
          onClick={() => {
            setEditingId(null);
            setForm(INITIAL_FORM);
            if (formSectionRef.current) {
              formSectionRef.current.scrollIntoView({ behavior: 'smooth' });
            }
          }}
        >
          + Add New Listing
        </Button>
      </div>

      {actionMsg && (
        <Alert variant="success" title="Success" onDismiss={() => setActionMsg('')}>
          {actionMsg}
        </Alert>
      )}

      {error && (
        <Alert variant="error" title="Notice" onDismiss={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* Overview Stats Bar */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '1rem',
          marginBottom: '1.5rem',
        }}
      >
        <div style={{ background: 'var(--sn-surface-soft)', padding: '1rem', borderRadius: 'var(--sn-radius-md)', border: '1px solid var(--sn-line)' }}>
          <span className="card-meta" style={{ display: 'block' }}>Total Listings</span>
          <strong style={{ fontSize: '1.4rem', color: 'var(--sn-ink)' }}>{listings.length}</strong>
        </div>
        <div style={{ background: 'var(--sn-surface-soft)', padding: '1rem', borderRadius: 'var(--sn-radius-md)', border: '1px solid var(--sn-line)' }}>
          <span className="card-meta" style={{ display: 'block' }}>Live & Approved</span>
          <strong style={{ fontSize: '1.4rem', color: 'var(--sn-success)' }}>
            {listings.filter((l) => l.status === 'APPROVED').length}
          </strong>
        </div>
        <div style={{ background: 'var(--sn-surface-soft)', padding: '1rem', borderRadius: 'var(--sn-radius-md)', border: '1px solid var(--sn-line)' }}>
          <span className="card-meta" style={{ display: 'block' }}>Pending Moderation</span>
          <strong style={{ fontSize: '1.4rem', color: 'var(--sn-warning-ink)' }}>
            {listings.filter((l) => l.status === 'PENDING_APPROVAL').length}
          </strong>
        </div>
      </div>

      {/* Owned Listings List */}
      <div style={{ marginBottom: '2.5rem' }}>
        <h3 style={{ marginBottom: '1rem' }}>My Properties ({listings.length})</h3>

        {loading && (
          <div className="loading-state" role="status">
            <Spinner size="lg" label="Loading listings…" />
            <p>Loading…</p>
          </div>
        )}

        {!loading && listings.length === 0 && (
          <div className="empty-state">
            <p style={{ fontWeight: 600, fontSize: 'var(--sn-text-base)', marginBottom: '0.5rem' }}>
              No listings created yet.
            </p>
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => {
                if (formSectionRef.current) formSectionRef.current.scrollIntoView({ behavior: 'smooth' });
              }}
            >
              Create a Listing
            </Button>
          </div>
        )}

        {!loading && listings.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {listings.map((l) => {
              const comp = evaluateCompleteness(l);
              const isRemoved = l.status === 'REMOVED';
              const firstPhoto = l.photos?.[0];
              const isExpanded = expandedCompletenessId === l.id;

              return (
                <Card
                  key={l.id}
                  as="article"
                  style={{
                    opacity: isRemoved ? 0.75 : 1,
                    borderLeft: isRemoved
                      ? '4px solid var(--sn-line-strong)'
                      : l.status === 'APPROVED'
                      ? '4px solid var(--sn-success)'
                      : '4px solid var(--sn-warning)',
                  }}
                >
                  <div style={{ display: 'grid', gridTemplateColumns: firstPhoto ? '140px 1fr' : '1fr', gap: '1.25rem', alignItems: 'start' }}>
                    {firstPhoto && (
                      <img
                        src={firstPhoto}
                        alt={l.title}
                        style={{
                          width: '100%',
                          height: '110px',
                          objectFit: 'cover',
                          borderRadius: 'var(--sn-radius-sm)',
                        }}
                        loading="lazy"
                      />
                    )}

                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <h4 style={{ margin: 0, fontSize: '1.15rem' }}>
                            <Link to={`/listings/${l.id}`} style={{ color: 'inherit' }}>
                              {l.title}
                            </Link>
                          </h4>
                          <span className="card-meta">#{l.id}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                          {getStatusBadge(l.status)}
                          <button
                            type="button"
                            onClick={() => setExpandedCompletenessId(isExpanded ? null : l.id)}
                            style={{
                              background: 'none',
                              border: 'none',
                              padding: 0,
                              cursor: 'pointer',
                            }}
                            aria-expanded={isExpanded}
                            aria-label={`Toggle completeness breakdown for listing #${l.id}`}
                          >
                            <Badge variant={comp.isComplete ? 'success' : 'warning'}>
                              {comp.score}% Complete {isExpanded ? '▲' : '▼'}
                            </Badge>
                          </button>
                        </div>
                      </div>

                      <p className="card-meta" style={{ marginBottom: '0.5rem' }}>
                        {l.address}, {l.city}, {l.state} {l.zip} &bull; ${l.price_per_night}/night &bull; Up to {l.max_guests} guests ({l.bedrooms} beds, {l.bathrooms} baths)
                      </p>

                      {/* Completeness breakdown dropdown */}
                      {isExpanded && (
                        <div
                          style={{
                            background: 'var(--sn-surface-soft)',
                            padding: '0.75rem',
                            borderRadius: 'var(--sn-radius-sm)',
                            marginBottom: '0.75rem',
                            fontSize: 'var(--sn-text-xs)',
                          }}
                        >
                          <strong>Listing Completeness Checklist:</strong>
                          <ul style={{ margin: '0.35rem 0 0', paddingLeft: '1.25rem' }}>
                            {comp.checks.map((chk) => (
                              <li key={chk.id} style={{ color: chk.ok ? 'var(--sn-success)' : 'var(--sn-warning-ink)' }}>
                                {chk.ok ? '✓' : '✗'} {chk.label}
                              </li>
                            ))}
                          </ul>
                          {!comp.isComplete && (
                            <p style={{ margin: '0.35rem 0 0', color: 'var(--sn-warning-ink)' }}>
                              Missing: {comp.missing.join(', ')}
                            </p>
                          )}
                        </div>
                      )}

                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', fontSize: 'var(--sn-text-xs)', color: 'var(--sn-ink-muted)', marginBottom: '0.75rem' }}>
                        <span>Check-in: {l.check_in_time || '15:00'}</span>
                        <span>&bull;</span>
                        <span>Check-out: {l.check_out_time || '11:00'}</span>
                        <span>&bull;</span>
                        <span>Hours: {l.operating_start_time || '00:00'}–{l.operating_end_time || '23:59'}</span>
                        <span>&bull;</span>
                        <span>{l.photos?.length || 0} photo(s)</span>
                        <span>&bull;</span>
                        <span>{l.videos?.length || 0} video(s)</span>
                        {l.lat != null && l.lng != null && (
                          <>
                            <span>&bull;</span>
                            <a
                              href={`https://www.google.com/maps/search/?api=1&query=${l.lat},${l.lng}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ textDecoration: 'underline' }}
                            >
                              📍 Google Map
                            </a>
                          </>
                        )}
                      </div>

                      {/* Status contextual notes */}
                      {l.status === 'PENDING_APPROVAL' && (
                        <p style={{ fontSize: 'var(--sn-text-xs)', color: 'var(--sn-warning-ink)', margin: '0 0 0.5rem' }}>
                          Awaiting approval. Hidden from search until then.
                        </p>
                      )}
                      {l.status === 'APPROVED' && (
                        <p style={{ fontSize: 'var(--sn-text-xs)', color: 'var(--sn-success)', margin: '0 0 0.5rem' }}>
                          Live in search.
                        </p>
                      )}

                      {/* Actions */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          onClick={() => startEdit(l)}
                        >
                          Edit Listing
                        </Button>

                        {!isRemoved && removeConfirmId !== l.id && (
                          <Button
                            type="button"
                            variant="danger"
                            size="sm"
                            onClick={() => setRemoveConfirmId(l.id)}
                          >
                            Remove
                          </Button>
                        )}

                        {removeConfirmId === l.id && (
                          <div
                            role="group"
                            aria-label={`Confirm removing listing #${l.id}`}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.5rem',
                              background: 'var(--sn-danger-tint)',
                              padding: '0.25rem 0.5rem',
                              borderRadius: 'var(--sn-radius-sm)',
                            }}
                          >
                            <span style={{ fontSize: 'var(--sn-text-xs)', color: 'var(--sn-danger)', fontWeight: 600 }}>
                              Archive this listing?
                            </span>
                            <Button
                              type="button"
                              variant="danger"
                              size="sm"
                              onClick={() => handleRemove(l.id)}
                            >
                              Confirm
                            </Button>
                            <Button
                              type="button"
                              variant="secondary"
                              size="sm"
                              onClick={() => setRemoveConfirmId(null)}
                            >
                              Cancel
                            </Button>
                          </div>
                        )}

                        <Link to={`/listings/${l.id}`} className="btn btn-ghost btn-sm">
                          View Public Page &rarr;
                        </Link>
                      </div>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Structured Host Form Section */}
      <div ref={formSectionRef} style={{ borderTop: '2px solid var(--sn-line)', paddingTop: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ margin: 0 }}>
              {editingId ? `Edit Listing #${editingId}` : 'Add a New Vacation Rental'}
            </h3>
            <p className="card-meta" style={{ margin: '0.25rem 0 0' }}>
              New and edited listings are reviewed before they appear in search.
            </p>
          </div>
          {editingId && (
            <Button type="button" variant="secondary" size="sm" onClick={cancelEdit}>
              Cancel Edit
            </Button>
          )}
        </div>

        <form onSubmit={handleSubmit} aria-label="Host rental listing creation and edit form">
          {/* Section 1: Property Identity & Description */}
          <fieldset style={{ border: '1px solid var(--sn-line)', borderRadius: 'var(--sn-radius-md)', padding: '1.25rem', marginBottom: '1.5rem', background: 'var(--sn-surface)' }}>
            <legend style={{ fontWeight: 700, padding: '0 0.5rem', color: 'var(--sn-ink)' }}>
              1. Property Identity & Details
            </legend>

            <div className="field-group">
              <label htmlFor="host-title">Property Title *</label>
              <input
                id="host-title"
                required
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="e.g., Waterfront Modern Loft with Bay Views"
              />
            </div>

            <div className="field-group">
              <label htmlFor="host-description">Full Description *</label>
              <textarea
                id="host-description"
                required
                rows={4}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Describe the architectural style, neighborhood atmosphere, views, proximity to attractions, and unique amenities…"
              />
            </div>
          </fieldset>

          {/* Section 2: Host Identity & Contact Information (Requirement 4.1) */}
          <fieldset style={{ border: '1px solid var(--sn-line)', borderRadius: 'var(--sn-radius-md)', padding: '1.25rem', marginBottom: '1.5rem', background: 'var(--sn-surface)' }}>
            <legend style={{ fontWeight: 700, padding: '0 0.5rem', color: 'var(--sn-ink)' }}>
              2. Host Identity & Contact Information
            </legend>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
              <div className="field-group">
                <label htmlFor="host-contact-name">Host / Contact Name</label>
                <input
                  id="host-contact-name"
                  value={form.host_contact_name}
                  onChange={(e) => setForm({ ...form, host_contact_name: e.target.value })}
                  placeholder="e.g., Sarah Jenkins"
                />
              </div>

              <div className="field-group">
                <label htmlFor="host-contact-email">Contact Email</label>
                <input
                  id="host-contact-email"
                  type="email"
                  value={form.host_contact_email}
                  onChange={(e) => setForm({ ...form, host_contact_email: e.target.value })}
                  placeholder="e.g., sarah@example.com"
                />
              </div>

              <div className="field-group">
                <label htmlFor="host-contact-phone">Contact Phone</label>
                <input
                  id="host-contact-phone"
                  type="tel"
                  value={form.host_contact_phone}
                  onChange={(e) => setForm({ ...form, host_contact_phone: e.target.value })}
                  placeholder="e.g., 408-555-0199"
                />
                <span className="field-hint">7 to 15 digits for verified guest support.</span>
              </div>
            </div>
          </fieldset>

          {/* Section 3: Location, Address Lookup & Coordinates (Requirement 4.1) */}
          <fieldset style={{ border: '1px solid var(--sn-line)', borderRadius: 'var(--sn-radius-md)', padding: '1.25rem', marginBottom: '1.5rem', background: 'var(--sn-surface)' }}>
            <legend style={{ fontWeight: 700, padding: '0 0.5rem', color: 'var(--sn-ink)' }}>
              3. Location & Address Geocoding
            </legend>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: '0.75rem' }}>
              <div className="field-group" style={{ position: 'relative' }}>
                <label htmlFor="host-address">Street Address *</label>
                <input
                  id="host-address"
                  autoComplete="off"
                  required
                  value={form.address}
                  onChange={(e) => { setForm({ ...form, address: e.target.value }); addressAC.query(e.target.value); }}
                  placeholder={hasGoogleMaps ? 'Start typing — Google Maps will suggest addresses' : 'e.g., 100 Demo Street'}
                />
                <PlaceSuggestions ac={addressAC} label="Address suggestions" />
              </div>

              <div className="field-group">
                <label htmlFor="host-city">City *</label>
                <input
                  id="host-city"
                  required
                  value={form.city}
                  onChange={(e) => setForm({ ...form, city: e.target.value })}
                />
              </div>

              <div className="field-group">
                <label htmlFor="host-state">State *</label>
                <input
                  id="host-state"
                  required
                  maxLength={2}
                  value={form.state}
                  onChange={(e) => setForm({ ...form, state: e.target.value.toUpperCase() })}
                  placeholder="CA"
                />
              </div>

              <div className="field-group">
                <label htmlFor="host-zip">ZIP Code *</label>
                <input
                  id="host-zip"
                  required
                  value={form.zip}
                  onChange={(e) => setForm({ ...form, zip: e.target.value })}
                  placeholder="95110"
                />
              </div>
            </div>

            {/* Address Lookup Action Button */}
            <div style={{ margin: '0.5rem 0 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                isLoading={isLookingUp}
                loadingText="Looking up coordinates…"
                onClick={handleAddressLookup}
              >
                📍 Look up coordinates from address
              </Button>
            </div>

            {lookupMsg && (
              <Alert variant={lookupMsg.type === 'success' ? 'success' : 'error'} style={{ marginBottom: '1rem' }}>
                {lookupMsg.text}
              </Alert>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="field-group">
                <label htmlFor="host-lat">Latitude * (-90 to 90)</label>
                <input
                  id="host-lat"
                  type="number"
                  step="any"
                  min="-90"
                  max="90"
                  required
                  value={form.lat}
                  onChange={(e) => setForm({ ...form, lat: e.target.value })}
                />
              </div>

              <div className="field-group">
                <label htmlFor="host-lng">Longitude * (-180 to 180)</label>
                <input
                  id="host-lng"
                  type="number"
                  step="any"
                  min="-180"
                  max="180"
                  required
                  value={form.lng}
                  onChange={(e) => setForm({ ...form, lng: e.target.value })}
                />
              </div>
            </div>

            {Number.isFinite(Number(form.lat)) && Number.isFinite(Number(form.lng)) && form.lat !== '' && form.lng !== '' && (
              <div style={{ marginTop: '1rem' }}>
                <span className="card-meta" style={{ display: 'block', marginBottom: '0.5rem' }}>Location preview:</span>
                <MapView listings={[{ id: 0, title: form.title || 'Your listing', address: form.address, city: form.city, lat: form.lat, lng: form.lng }]} selectedId={0} />
              </div>
            )}
          </fieldset>

          {/* Section 4: Operating Hours & Booking Times (Requirement 4.1) */}
          <fieldset style={{ border: '1px solid var(--sn-line)', borderRadius: 'var(--sn-radius-md)', padding: '1.25rem', marginBottom: '1.5rem', background: 'var(--sn-surface)' }}>
            <legend style={{ fontWeight: 700, padding: '0 0.5rem', color: 'var(--sn-ink)' }}>
              4. Operating Hours & Available Booking Times
            </legend>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
              <div className="field-group">
                <label htmlFor="host-start-time">Operating Start Time</label>
                <input
                  id="host-start-time"
                  type="time"
                  value={form.operating_start_time}
                  onChange={(e) => setForm({ ...form, operating_start_time: e.target.value })}
                />
              </div>

              <div className="field-group">
                <label htmlFor="host-end-time">Operating End Time</label>
                <input
                  id="host-end-time"
                  type="time"
                  value={form.operating_end_time}
                  onChange={(e) => setForm({ ...form, operating_end_time: e.target.value })}
                />
              </div>

              <div className="field-group">
                <label htmlFor="host-checkin-time">Daily Check-in Time</label>
                <input
                  id="host-checkin-time"
                  type="time"
                  value={form.check_in_time}
                  onChange={(e) => setForm({ ...form, check_in_time: e.target.value })}
                />
              </div>

              <div className="field-group">
                <label htmlFor="host-checkout-time">Daily Check-out Time</label>
                <input
                  id="host-checkout-time"
                  type="time"
                  value={form.check_out_time}
                  onChange={(e) => setForm({ ...form, check_out_time: e.target.value })}
                />
              </div>
            </div>

            <div className="field-group">
              <label htmlFor="host-available-times">Available Booking Schedule & Description</label>
              <input
                id="host-available-times"
                value={form.available_times}
                onChange={(e) => setForm({ ...form, available_times: e.target.value })}
                placeholder="e.g., Check-in 3pm, check-out 11am; available year-round unless booked"
              />
            </div>
          </fieldset>

          {/* Section 5: Capacity & Pricing */}
          <fieldset style={{ border: '1px solid var(--sn-line)', borderRadius: 'var(--sn-radius-md)', padding: '1.25rem', marginBottom: '1.5rem', background: 'var(--sn-surface)' }}>
            <legend style={{ fontWeight: 700, padding: '0 0.5rem', color: 'var(--sn-ink)' }}>
              5. Capacity & Pricing
            </legend>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '1rem' }}>
              <div className="field-group">
                <label htmlFor="host-price">Price / Night (USD) *</label>
                <input
                  id="host-price"
                  type="number"
                  min="1"
                  required
                  value={form.price_per_night}
                  onChange={(e) => setForm({ ...form, price_per_night: e.target.value })}
                />
              </div>

              <div className="field-group">
                <label htmlFor="host-guests">Max Guests *</label>
                <input
                  id="host-guests"
                  type="number"
                  min="1"
                  required
                  value={form.max_guests}
                  onChange={(e) => setForm({ ...form, max_guests: e.target.value })}
                />
              </div>

              <div className="field-group">
                <label htmlFor="host-bedrooms">Bedrooms *</label>
                <input
                  id="host-bedrooms"
                  type="number"
                  min="0"
                  required
                  value={form.bedrooms}
                  onChange={(e) => setForm({ ...form, bedrooms: e.target.value })}
                />
              </div>

              <div className="field-group">
                <label htmlFor="host-bathrooms">Bathrooms *</label>
                <input
                  id="host-bathrooms"
                  type="number"
                  min="0"
                  required
                  value={form.bathrooms}
                  onChange={(e) => setForm({ ...form, bathrooms: e.target.value })}
                />
              </div>
            </div>
          </fieldset>

          {/* Section 6: Amenities Selection */}
          <fieldset style={{ border: '1px solid var(--sn-line)', borderRadius: 'var(--sn-radius-md)', padding: '1.25rem', marginBottom: '1.5rem', background: 'var(--sn-surface)' }}>
            <legend style={{ fontWeight: 700, padding: '0 0.5rem', color: 'var(--sn-ink)' }}>
              6. Property Amenities
            </legend>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                gap: '0.5rem',
                marginBottom: '1rem',
              }}
            >
              {POPULAR_AMENITIES.map((amenity) => {
                const checked = form.amenities.includes(amenity);
                return (
                  <label
                    key={amenity}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      fontWeight: 500,
                      cursor: 'pointer',
                      padding: '0.35rem 0.5rem',
                      borderRadius: 'var(--sn-radius-sm)',
                      background: checked ? 'var(--sn-primary-tint)' : 'transparent',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleAmenityToggle(amenity)}
                      style={{ width: 'auto', minHeight: 'auto' }}
                    />
                    <span>{amenity}</span>
                  </label>
                );
              })}
            </div>

            <div className="field-group">
              <label htmlFor="host-custom-amenities">Additional Amenities (comma-separated)</label>
              <input
                id="host-custom-amenities"
                value={form.customAmenities}
                onChange={(e) => setForm({ ...form, customAmenities: e.target.value })}
                placeholder="e.g., EV Charger, Fire Pit, Board Games, Espresso Machine"
              />
            </div>
          </fieldset>

          {/* Section 7: Media (Photos & Videos) */}
          <fieldset style={{ border: '1px solid var(--sn-line)', borderRadius: 'var(--sn-radius-md)', padding: '1.25rem', marginBottom: '1.5rem', background: 'var(--sn-surface)' }}>
            <legend style={{ fontWeight: 700, padding: '0 0.5rem', color: 'var(--sn-ink)' }}>
              7. Media (Photos & Videos)
            </legend>

            <div className="field-group">
              <label htmlFor="host-upload">Upload photos or videos from your device</label>
              <input
                id="host-upload"
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp,image/gif,video/mp4,video/webm"
                onChange={handleFiles}
                disabled={uploading}
              />
              {uploading && <span className="card-meta">Uploading…</span>}
              {uploadMsg && <Alert variant={uploadMsg.type === 'error' ? 'error' : 'success'}>{uploadMsg.text}</Alert>}
            </div>

            <div className="field-group">
              <label htmlFor="host-photos">Photo URLs (uploaded files appear here; one per line or comma-separated)</label>
              <textarea
                id="host-photos"
                rows={3}
                value={form.photos}
                onChange={(e) => setForm({ ...form, photos: e.target.value })}
                placeholder="https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&#10;https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800"
              />
            </div>

            {/* Live photo preview grid */}
            {previewPhotos.length > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <span className="card-meta" style={{ display: 'block', marginBottom: '0.5rem' }}>
                  Photo Previews ({previewPhotos.length}):
                </span>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {previewPhotos.slice(0, 6).map((url, idx) => (
                    <img
                      key={idx}
                      src={url}
                      alt={`Preview ${idx + 1}`}
                      style={{
                        width: '80px',
                        height: '60px',
                        objectFit: 'cover',
                        borderRadius: 'var(--sn-radius-sm)',
                        border: '1px solid var(--sn-line)',
                      }}
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  ))}
                </div>
              </div>
            )}

            <div className="field-group">
              <label htmlFor="host-videos">Optional Video URLs (one per line or comma-separated)</label>
              <textarea
                id="host-videos"
                rows={2}
                value={form.videos}
                onChange={(e) => setForm({ ...form, videos: e.target.value })}
                placeholder="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
              />
            </div>
          </fieldset>

          {/* Form Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isSubmitting}
              loadingText={editingId ? 'Saving changes…' : 'Submitting listing…'}
            >
              {editingId ? 'Save Changes & Re-submit' : 'Create Listing (Submit for Approval)'}
            </Button>

            {editingId && (
              <Button type="button" variant="secondary" size="lg" onClick={cancelEdit}>
                Cancel Edit
              </Button>
            )}
          </div>
        </form>
      </div>
    </section>
  );
}
