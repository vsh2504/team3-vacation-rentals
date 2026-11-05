// Frontend — Owner: Manoj (Manoj Ganjigatte Manjunatha)
// Feature: Book & Cancel a Stay — booking form component.
// Used by ListingDetailPage (Vinayak's page) to reserve a stay.
// Enforces StayNest booking invariants with clear loading, validation,
// conflict, and confirmed booking states (Requirements 3.1, 3.2, 8.2, 8.3, 8.4).
import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api/client.js';
import { Alert, Badge, Button } from './ui/index.js';

export default function BookingForm({ auth, listingId }) {
  const [sp] = useSearchParams();
  const todayStr = new Date().toISOString().slice(0, 10);

  const [checkIn, setCheckIn] = useState(() => sp.get('check_in') || '');
  const [checkOut, setCheckOut] = useState(() => sp.get('check_out') || '');
  const [checkInTime, setCheckInTime] = useState(() => sp.get('check_in_time') || '15:00');
  const [checkOutTime, setCheckOutTime] = useState(() => sp.get('check_out_time') || '11:00');
  const [guests, setGuests] = useState(() => {
    const g = Number(sp.get('guests'));
    return g > 0 ? g : 2;
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmedBooking, setConfirmedBooking] = useState(null);
  const [error, setError] = useState('');

  // Calculate stay duration in nights
  const nights = checkIn && checkOut
    ? Math.round((new Date(`${checkOut}T00:00:00`) - new Date(`${checkIn}T00:00:00`)) / (1000 * 60 * 60 * 24))
    : 0;

  const isStayTooLong = nights > 14;
  const isInvalidDateRange = checkIn && checkOut && nights <= 0;

  async function handleBook(e) {
    e.preventDefault();
    setError('');

    if (!auth) {
      setError('Please log in as a Customer to book this stay.');
      return;
    }

    if (auth.user?.role !== 'CUSTOMER') {
      setError(`Signed in as ${auth.user?.role || 'user'}. Only customer accounts can book stays. Please switch to a customer account.`);
      return;
    }

    if (isInvalidDateRange) {
      setError('Check-out date must be strictly after check-in date.');
      return;
    }

    if (isStayTooLong) {
      setError('Stays cannot exceed 14 nights (StayNest policy). Please select a shorter duration.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        listing_id: Number(listingId),
        check_in: checkIn,
        check_out: checkOut,
        check_in_time: checkInTime,
        check_out_time: checkOutTime,
        guests: Number(guests),
      };

      const result = await api.book(auth.token, payload);
      setConfirmedBooking(result);
    } catch (err) {
      setError(err.message || 'Failed to complete booking. Please try different dates.');
    } finally {
      setIsSubmitting(false);
    }
  }

  // Confirmed booking success state
  if (confirmedBooking) {
    return (
      <div className="booking-card" style={{ borderColor: 'var(--sn-success)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <h3 style={{ margin: 0, color: 'var(--sn-success-ink)' }}>Booking Confirmed!</h3>
          <Badge variant="success">CONFIRMED</Badge>
        </div>

        <Alert variant="success" title="Your reservation is secured">
          Stay confirmed for <strong>{confirmedBooking.guests} guest{confirmedBooking.guests === 1 ? '' : 's'}</strong>.
        </Alert>

        <div style={{ background: 'var(--sn-surface-soft)', padding: '1rem', borderRadius: 'var(--sn-radius-sm)', margin: '1rem 0' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: 'var(--sn-text-sm)' }}>
            <div>
              <span className="card-meta" style={{ display: 'block' }}>Booking Reference</span>
              <strong>#{confirmedBooking.id}</strong>
            </div>
            <div>
              <span className="card-meta" style={{ display: 'block' }}>Total Price</span>
              <strong style={{ fontSize: '1.1rem', color: 'var(--sn-primary)' }}>${confirmedBooking.total_price}</strong>
            </div>
            <div>
              <span className="card-meta" style={{ display: 'block' }}>Check-in</span>
              <strong>{confirmedBooking.check_in}</strong> at {confirmedBooking.check_in_time || '15:00'}
            </div>
            <div>
              <span className="card-meta" style={{ display: 'block' }}>Check-out</span>
              <strong>{confirmedBooking.check_out}</strong> at {confirmedBooking.check_out_time || '11:00'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '1rem' }}>
          <Link to="/bookings" className="btn btn-primary btn-block" style={{ textAlign: 'center' }}>
            Go to My Bookings
          </Link>
          <Button
            type="button"
            variant="secondary"
            className="btn-block"
            onClick={() => setConfirmedBooking(null)}
          >
            Book Another Stay
          </Button>
        </div>
      </div>
    );
  }

  const isCustomer = auth?.user?.role === 'CUSTOMER';

  return (
    <div className="booking-card">
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <h3 style={{ margin: 0 }}>Reserve this stay</h3>
        <span className="card-meta">Max stay 14 nights</span>
      </div>

      {!auth && (
        <Alert variant="info" title="Customer sign-in required">
          Please <Link to="/auth" style={{ fontWeight: 600, textDecoration: 'underline' }}>sign in as a customer</Link> to reserve this home.
        </Alert>
      )}

      {auth && !isCustomer && (
        <Alert variant="warning" title="Account role notice">
          You are signed in as <strong>{auth.user?.role}</strong>. Only customer accounts can book stays. Switch to a customer account to complete a reservation.
        </Alert>
      )}

      <form onSubmit={handleBook} aria-label="Book listing reservation form">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem' }}>
          <div className="field-group">
            <label htmlFor="booking-checkin">Check-in date</label>
            <input
              id="booking-checkin"
              type="date"
              required
              min={todayStr}
              value={checkIn}
              onChange={e => setCheckIn(e.target.value)}
              aria-invalid={isInvalidDateRange ? 'true' : undefined}
            />
          </div>

          <div className="field-group">
            <label htmlFor="booking-checkin-time">Check-in time</label>
            <input
              id="booking-checkin-time"
              type="time"
              value={checkInTime}
              onChange={e => setCheckInTime(e.target.value)}
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem' }}>
          <div className="field-group">
            <label htmlFor="booking-checkout">Check-out date</label>
            <input
              id="booking-checkout"
              type="date"
              required
              min={checkIn || todayStr}
              value={checkOut}
              onChange={e => setCheckOut(e.target.value)}
              aria-invalid={isInvalidDateRange || isStayTooLong ? 'true' : undefined}
              aria-describedby="booking-stay-duration"
            />
          </div>

          <div className="field-group">
            <label htmlFor="booking-checkout-time">Check-out time</label>
            <input
              id="booking-checkout-time"
              type="time"
              value={checkOutTime}
              onChange={e => setCheckOutTime(e.target.value)}
            />
          </div>
        </div>

        <div className="field-group">
          <label htmlFor="booking-guests">Number of guests</label>
          <input
            id="booking-guests"
            type="number"
            min="1"
            max="100"
            required
            value={guests}
            onChange={e => setGuests(Number(e.target.value))}
          />
        </div>

        {/* Live stay duration and validation feedback */}
        <div id="booking-stay-duration" style={{ marginBottom: '1rem' }}>
          {nights > 0 && !isStayTooLong && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.5rem 0.75rem', background: 'var(--sn-surface-soft)', borderRadius: 'var(--sn-radius-sm)', fontSize: 'var(--sn-text-sm)' }}>
              <span>Duration:</span>
              <strong>{nights} night{nights === 1 ? '' : 's'}</strong>
            </div>
          )}
          {isInvalidDateRange && (
            <p className="field-error" role="alert">Check-out date must be after check-in date.</p>
          )}
          {isStayTooLong && (
            <p className="field-error" role="alert">Maximum stay is 14 nights (selected: {nights} nights).</p>
          )}
        </div>

        <Button
          type="submit"
          variant="primary"
          className="btn-block"
          isLoading={isSubmitting}
          loadingText="Securing reservation…"
          disabled={!auth || !isCustomer || isInvalidDateRange || isStayTooLong || !checkIn || !checkOut}
        >
          Book Now
        </Button>
      </form>

      {error && (
        <Alert variant="error" id="booking-error" className="field-error" title="Unable to confirm booking">
          {error}
        </Alert>
      )}
    </div>
  );
}
