// Frontend — Owner: Prajval Sudhir
// Feature: Trust, Reviews & Analytics — review form component.
// Used by BookingsPage (Manoj's page) for COMPLETED bookings only;
// the API enforces past/owned/once, this component only collects
// rating 1-5 + comment and shows the API's message.
import React, { useState } from 'react';
import { api } from '../api/client.js';
export default function ReviewForm({ auth, bookingId, onSubmitted }) {
  const [rating, setRating] = useState(5); const [comment, setComment] = useState('');
  const [error, setError] = useState('');
  async function submit(e) {
    e.preventDefault(); setError('');
    try { await api.review(auth.token, { booking_id: bookingId, rating: Number(rating), comment }); onSubmitted(); }
    catch (err) { setError(err.message); }
  }
  return (
    <form onSubmit={submit} style={{ display: 'inline' }}>
      <label>Rating <select value={rating} onChange={e => setRating(e.target.value)}><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>{' '}
      <label>Comment <input value={comment} onChange={e => setComment(e.target.value)} /></label>{' '}
      <button type="submit">Submit review</button>
      {error && <span role="alert"> {error}</span>}
    </form>
  );
}
