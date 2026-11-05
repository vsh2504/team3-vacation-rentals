// Frontend — Owner: Manoj (Manoj Ganjigatte Manjunatha)
// Feature: Book & Cancel a Stay — customer bookings management.
// Displays upcoming, completed, and cancelled stays with OpenStreetMap links,
// cancel workflows, completion triggers, and review submission (Requirements 3.1-3.6, 8.2-8.4).
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import ReviewForm from '../components/ReviewForm.jsx';
import { Alert, Badge, Button, Card, Spinner } from '../components/ui/index.js';

export default function BookingsPage({ auth }) {
  const [bookings, setListingsBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');
  const [actionBusyId, setActionBusyId] = useState(null);
  const [cancelConfirmId, setCancelConfirmId] = useState(null);
  const [activeTab, setActiveTab] = useState('all');
  const [reviewedBookingIds, setReviewedBookingIds] = useState(new Set());

  const todayStr = new Date().toISOString().slice(0, 10);

  function loadBookings() {
    if (!auth) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');
    api.myBookings(auth.token)
      .then((data) => {
        setListingsBookings(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load your bookings.');
      })
      .finally(() => {
        setLoading(false);
      });
  }

  useEffect(() => {
    loadBookings();
  }, [auth]); // eslint-disable-line

  if (!auth) {
    return (
      <section aria-labelledby="bookings-heading">
        <h2 id="bookings-heading">My Bookings</h2>
        <Card>
          <div className="empty-state" style={{ margin: 0 }}>
            <h3>Customer sign-in required</h3>
            <p style={{ marginBottom: '1rem' }}>
              Please sign in to view your upcoming stays, past trips, and reservation details.
            </p>
            <Link to="/auth" className="btn btn-primary">
              Sign In / Register
            </Link>
          </div>
        </Card>
      </section>
    );
  }

  // Segment stays
  const cancelledStays = bookings.filter(
    (b) => b.status === 'CANCELLED' || b.stay_state === 'cancelled'
  );
  const upcomingStays = bookings.filter(
    (b) => b.status === 'CONFIRMED' && b.check_out > todayStr && b.stay_state !== 'cancelled'
  );
  const pastStays = bookings.filter(
    (b) => (b.status === 'COMPLETED' || (b.status === 'CONFIRMED' && b.check_out <= todayStr)) &&
           b.status !== 'CANCELLED' && b.stay_state !== 'cancelled'
  );

  let displayedBookings = bookings;
  if (activeTab === 'upcoming') displayedBookings = upcomingStays;
  else if (activeTab === 'past') displayedBookings = pastStays;
  else if (activeTab === 'cancelled') displayedBookings = cancelledStays;

  async function handleCancel(bookingId) {
    setError('');
    setActionSuccess('');
    setActionBusyId(bookingId);
    try {
      await api.cancelBooking(auth.token, bookingId);
      setActionSuccess(`Booking #${bookingId} has been successfully cancelled. The dates have been released.`);
      setCancelConfirmId(null);
      loadBookings();
    } catch (err) {
      setError(err.message || `Failed to cancel booking #${bookingId}.`);
    } finally {
      setActionBusyId(null);
    }
  }

  async function handleComplete(bookingId) {
    setError('');
    setActionSuccess('');
    setActionBusyId(bookingId);
    try {
      await api.completeBooking(auth.token, bookingId);
      setActionSuccess(`Stay #${bookingId} marked as completed! You can now write a review.`);
      loadBookings();
    } catch (err) {
      setError(err.message || `Failed to mark booking #${bookingId} as completed.`);
    } finally {
      setActionBusyId(null);
    }
  }

  function handleReviewSubmitted(bookingId) {
    setReviewedBookingIds((prev) => new Set([...prev, bookingId]));
    setActionSuccess(`Thank you! Your review for booking #${bookingId} has been recorded.`);
    loadBookings();
  }

  function getStatusBadge(status, stayState) {
    if (status === 'CANCELLED' || stayState === 'cancelled') {
      return <Badge variant="danger">CANCELLED</Badge>;
    }
    if (status === 'COMPLETED') {
      return <Badge variant="accent">COMPLETED</Badge>;
    }
    if (stayState === 'past') {
      return <Badge variant="neutral">STAY ENDED</Badge>;
    }
    return <Badge variant="success">CONFIRMED</Badge>;
  }

  function getMapUrl(b) {
    if (b.location?.map_url) return b.location.map_url;
    if (b.map_url) return b.map_url;
    if (b.location?.lat != null && b.location?.lng != null) {
      return `https://www.openstreetmap.org/?mlat=${b.location.lat}&mlon=${b.location.lng}#map=16/${b.location.lat}/${b.location.lng}`;
    }
    return null;
  }

  return (
    <section aria-labelledby="bookings-heading">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
        <div>
          <h2 id="bookings-heading" style={{ margin: 0 }}>My Bookings & Stays</h2>
          <p className="card-meta" style={{ margin: '0.25rem 0 0' }}>
            Manage upcoming reservations, view past trip details, and submit verified reviews.
          </p>
        </div>
        <Link to="/" className="btn btn-secondary btn-sm">
          Browse Rentals
        </Link>
      </div>

      {actionSuccess && (
        <Alert
          variant="success"
          title="Action confirmed"
          onDismiss={() => setActionSuccess('')}
        >
          {actionSuccess}
        </Alert>
      )}

      {error && (
        <Alert
          variant="error"
          title="Notice"
          onDismiss={() => setError('')}
        >
          {error}
        </Alert>
      )}

      {/* Stay Filter Tabs */}
      <div
        role="tablist"
        aria-label="Filter bookings by status"
        style={{
          display: 'flex',
          gap: '0.5rem',
          flexWrap: 'wrap',
          marginBottom: '1.25rem',
          borderBottom: '1px solid var(--sn-line)',
          paddingBottom: '0.5rem',
        }}
      >
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'all'}
          onClick={() => setActiveTab('all')}
          className={`btn btn-sm ${activeTab === 'all' ? 'btn-primary' : 'btn-ghost'}`}
        >
          All Stays ({bookings.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'upcoming'}
          onClick={() => setActiveTab('upcoming')}
          className={`btn btn-sm ${activeTab === 'upcoming' ? 'btn-primary' : 'btn-ghost'}`}
        >
          Upcoming ({upcomingStays.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'past'}
          onClick={() => setActiveTab('past')}
          className={`btn btn-sm ${activeTab === 'past' ? 'btn-primary' : 'btn-ghost'}`}
        >
          Past & Completed ({pastStays.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'cancelled'}
          onClick={() => setActiveTab('cancelled')}
          className={`btn btn-sm ${activeTab === 'cancelled' ? 'btn-primary' : 'btn-ghost'}`}
        >
          Cancelled ({cancelledStays.length})
        </button>
      </div>

      {loading && (
        <div className="loading-state" role="status">
          <Spinner size="lg" label="Loading your bookings…" />
          <p>Retrieving your reservation history…</p>
        </div>
      )}

      {!loading && displayedBookings.length === 0 && (
        <div className="empty-state">
          <p style={{ fontWeight: 600, fontSize: 'var(--sn-text-base)', marginBottom: '0.5rem' }}>
            {activeTab === 'upcoming' && 'No upcoming stays scheduled.'}
            {activeTab === 'past' && 'No past or completed stays.'}
            {activeTab === 'cancelled' && 'No cancelled reservations.'}
            {activeTab === 'all' && 'You have no bookings on record yet.'}
          </p>
          <p style={{ color: 'var(--sn-ink-muted)', marginBottom: '1rem' }}>
            Ready to plan your next trip? Explore curated homes across our destinations.
          </p>
          <Link to="/" className="btn btn-primary btn-sm">
            Find a Stay
          </Link>
        </div>
      )}

      {/* Bookings List */}
      {!loading && displayedBookings.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {displayedBookings.map((b) => {
            const mapUrl = getMapUrl(b);
            const isConfirmed = b.status === 'CONFIRMED';
            const isCompleted = b.status === 'COMPLETED';
            const isCancelled = b.status === 'CANCELLED' || b.stay_state === 'cancelled';
            const isPastConfirmed = isConfirmed && b.check_out <= todayStr;
            const hasReviewed = reviewedBookingIds.has(b.id);
            const isBusy = actionBusyId === b.id;
            const title = b.listing?.title || b.location?.name || `Listing #${b.listing_id}`;
            const photoUrl = b.listing?.photos?.[0];

            return (
              <Card
                key={b.id}
                as="article"
                style={{
                  borderLeft: isCancelled
                    ? '4px solid var(--sn-danger)'
                    : isCompleted
                    ? '4px solid var(--sn-accent)'
                    : '4px solid var(--sn-primary)',
                }}
              >
                <div style={{ display: 'grid', gridTemplateColumns: photoUrl ? '140px 1fr' : '1fr', gap: '1.25rem', alignItems: 'start' }}>
                  {photoUrl && (
                    <img
                      src={photoUrl}
                      alt={title}
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
                        <h3 style={{ margin: 0, fontSize: '1.15rem' }}>
                          <Link to={`/listings/${b.listing_id}`} style={{ color: 'inherit' }}>
                            {title}
                          </Link>
                        </h3>
                        <span className="card-meta">Booking #{b.id}</span>
                      </div>
                      <div>
                        {getStatusBadge(b.status, b.stay_state)}
                      </div>
                    </div>

                    {/* Address & OpenStreetMap link (Requirement 3.4) */}
                    <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.75rem', fontSize: 'var(--sn-text-sm)' }}>
                      <span style={{ color: 'var(--sn-ink-muted)' }}>
                        {b.location?.address ? `${b.location.address}, ${b.location.city}, ${b.location.state} ${b.location.zip}` : 'Location on record'}
                      </span>
                      {mapUrl && (
                        <a
                          href={mapUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-secondary btn-sm"
                          style={{ padding: '0.2rem 0.5rem', minHeight: '30px', fontSize: 'var(--sn-text-xs)' }}
                          aria-label={`Open ${title} location on OpenStreetMap (opens in new tab)`}
                        >
                          <span aria-hidden="true">📍</span> View on OpenStreetMap
                        </a>
                      )}
                    </div>

                    {/* Stay Specs Grid */}
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                        gap: '0.75rem',
                        background: 'var(--sn-surface-soft)',
                        padding: '0.75rem 1rem',
                        borderRadius: 'var(--sn-radius-sm)',
                        fontSize: 'var(--sn-text-sm)',
                        marginBottom: '0.75rem',
                      }}
                    >
                      <div>
                        <span className="card-meta" style={{ display: 'block' }}>Check-in</span>
                        <strong>{b.check_in}</strong>
                        <span style={{ display: 'block', fontSize: 'var(--sn-text-xs)', color: 'var(--sn-ink-muted)' }}>
                          at {b.check_in_time || '15:00'}
                        </span>
                      </div>

                      <div>
                        <span className="card-meta" style={{ display: 'block' }}>Check-out</span>
                        <strong>{b.check_out}</strong>
                        <span style={{ display: 'block', fontSize: 'var(--sn-text-xs)', color: 'var(--sn-ink-muted)' }}>
                          at {b.check_out_time || '11:00'}
                        </span>
                      </div>

                      <div>
                        <span className="card-meta" style={{ display: 'block' }}>Guests</span>
                        <strong>{b.guests} guest{b.guests === 1 ? '' : 's'}</strong>
                      </div>

                      <div>
                        <span className="card-meta" style={{ display: 'block' }}>Total Paid</span>
                        <strong style={{ color: 'var(--sn-primary)', fontSize: '1.05rem' }}>
                          ${b.total_price}
                        </strong>
                      </div>
                    </div>

                    {/* Cancelled details */}
                    {isCancelled && b.cancelled_at && (
                      <p className="card-meta" style={{ color: 'var(--sn-danger)' }}>
                        Cancelled on {new Date(b.cancelled_at).toLocaleString()}
                      </p>
                    )}

                    {/* Actions and status controls */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                      {/* Cancel Flow (Requirement 3.3) */}
                      {isConfirmed && cancelConfirmId !== b.id && (
                        <Button
                          type="button"
                          variant="danger"
                          size="sm"
                          disabled={isBusy}
                          onClick={() => setCancelConfirmId(b.id)}
                        >
                          Cancel Booking
                        </Button>
                      )}

                      {/* Cancel Confirmation Prompt */}
                      {cancelConfirmId === b.id && (
                        <div
                          role="group"
                          aria-label={`Confirm cancellation for booking #${b.id}`}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            background: 'var(--sn-danger-tint)',
                            padding: '0.4rem 0.75rem',
                            borderRadius: 'var(--sn-radius-sm)',
                          }}
                        >
                          <span style={{ fontSize: 'var(--sn-text-xs)', color: 'var(--sn-danger)', fontWeight: 600 }}>
                            Release this reservation?
                          </span>
                          <Button
                            type="button"
                            variant="danger"
                            size="sm"
                            isLoading={isBusy}
                            loadingText="Cancelling…"
                            onClick={() => handleCancel(b.id)}
                          >
                            Confirm Cancel
                          </Button>
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            disabled={isBusy}
                            onClick={() => setCancelConfirmId(null)}
                          >
                            Keep Stay
                          </Button>
                        </div>
                      )}

                      {/* Mark Completed trigger for ended stays */}
                      {isPastConfirmed && (
                        <Button
                          type="button"
                          variant="primary"
                          size="sm"
                          isLoading={isBusy}
                          loadingText="Completing…"
                          onClick={() => handleComplete(b.id)}
                        >
                          Mark Stay Completed
                        </Button>
                      )}

                      {/* Listing Link */}
                      <Link to={`/listings/${b.listing_id}`} className="btn btn-secondary btn-sm">
                        View Listing
                      </Link>
                    </div>

                    {/* Review Section (Requirements 3.5, 3.6) */}
                    {isCompleted && (
                      <div style={{ marginTop: '0.75rem' }}>
                        {hasReviewed ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                            <Badge variant="accent">★ Reviewed</Badge>
                            <span className="card-meta">You have submitted a review for this stay.</span>
                          </div>
                        ) : (
                          <ReviewForm
                            auth={auth}
                            bookingId={b.id}
                            onSubmitted={() => handleReviewSubmitted(b.id)}
                          />
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </section>
  );
}
