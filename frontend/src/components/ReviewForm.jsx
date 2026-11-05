// Frontend — Owner: Prajval Sudhir
// Feature: Trust, Reviews & Analytics — review form component.
// Used by BookingsPage for completed stays.
// Enforces: rating 1-5, optional comment, one review per completed booking.
// Accessible with keyboard controls, star ratings, loading & error states (Requirements 3.5, 3.6, 8.3, 8.4).
import React, { useState } from 'react';
import { api } from '../api/client.js';
import { Alert, Button } from './ui/index.js';

export default function ReviewForm({ auth, bookingId, onSubmitted }) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const starLabels = {
    1: '1 Star — Poor',
    2: '2 Stars — Fair',
    3: '3 Stars — Good',
    4: '4 Stars — Very Good',
    5: '5 Stars — Excellent',
  };

  async function submit(e) {
    e.preventDefault();
    setError('');

    if (!auth) {
      setError('You must be logged in to review a stay.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await api.review(auth.token, {
        booking_id: Number(bookingId),
        rating: Number(rating),
        comment: comment.trim(),
      });
      setSuccess(true);
      if (typeof onSubmitted === 'function') {
        onSubmitted(res);
      }
    } catch (err) {
      setError(err.message || 'Unable to submit review. Reviews are allowed once on completed stays.');
    } finally {
      setIsSubmitting(false);
    }
  }

  if (success) {
    return (
      <div style={{ marginTop: '0.5rem' }}>
        <Alert variant="success" title="Review published">
          Thank you for rating your stay ★ {rating}/5! Your feedback helps the StayNest community.
        </Alert>
      </div>
    );
  }

  return (
    <form
      onSubmit={submit}
      aria-label={`Submit review for booking #${bookingId}`}
      style={{
        marginTop: '0.75rem',
        padding: '0.875rem',
        background: 'var(--sn-surface-soft)',
        border: '1px solid var(--sn-line)',
        borderRadius: 'var(--sn-radius-md)',
      }}
    >
      <fieldset style={{ border: 'none', margin: 0, padding: 0 }}>
        <legend style={{ fontWeight: 600, fontSize: 'var(--sn-text-sm)', color: 'var(--sn-ink)', marginBottom: '0.5rem' }}>
          Rate your completed stay
        </legend>

        {/* Accessible Star Rating Picker */}
        <div
          role="radiogroup"
          aria-label="Star rating from 1 to 5"
          style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}
        >
          {[1, 2, 3, 4, 5].map((star) => {
            const isSelected = rating === star;
            return (
              <button
                key={star}
                type="button"
                role="radio"
                aria-checked={isSelected}
                aria-label={starLabels[star]}
                onClick={() => setRating(star)}
                style={{
                  minHeight: '38px',
                  minWidth: '38px',
                  padding: '0.35rem 0.65rem',
                  borderRadius: 'var(--sn-radius-sm)',
                  border: isSelected ? '2px solid var(--sn-accent-ink)' : '1px solid var(--sn-line-strong)',
                  background: isSelected ? 'var(--sn-accent)' : 'var(--sn-surface)',
                  color: isSelected ? 'var(--sn-accent-ink)' : 'var(--sn-ink)',
                  fontWeight: isSelected ? 700 : 500,
                  fontSize: 'var(--sn-text-sm)',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                <span aria-hidden="true" style={{ color: isSelected ? 'inherit' : '#f59e0b' }}>★</span>
                <span>{star}</span>
              </button>
            );
          })}
          <span className="card-meta" style={{ marginLeft: '0.5rem', fontWeight: 600 }}>
            {starLabels[rating]}
          </span>
        </div>

        {/* Comment Input */}
        <div className="field-group" style={{ marginBottom: '0.75rem' }}>
          <label htmlFor={`review-comment-${bookingId}`} style={{ fontSize: 'var(--sn-text-xs)' }}>
            Review comment <span className="field-hint" style={{ display: 'inline' }}>(optional)</span>
          </label>
          <textarea
            id={`review-comment-${bookingId}`}
            rows={2}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Share details about the property, host, accuracy, or stay experience…"
            style={{ width: '100%', resize: 'vertical' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            isLoading={isSubmitting}
            loadingText="Submitting review…"
          >
            Submit Review
          </Button>
        </div>
      </fieldset>

      {error && (
        <Alert variant="error" className="field-error" style={{ marginTop: '0.75rem' }}>
          {error}
        </Alert>
      )}
    </form>
  );
}
