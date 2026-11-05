// Booking pre-flight checks as a Chain of Responsibility that stops at the
// first failing rule, so the customer sees one clear message at a time.
import { Rule, chain } from './chain.js';
import { nightsBetween } from './search.js';

export const stayNights = (checkIn, checkOut) =>
  (checkIn && checkOut ? nightsBetween(checkIn, checkOut) : 0);

const signedIn = new Rule((c, e) => {
  if (!c.auth) e.problem = 'Please log in as a Customer to book this stay.';
});
const customerOnly = new Rule((c, e) => {
  if (c.auth.user?.role !== 'CUSTOMER') {
    e.problem = `Signed in as ${c.auth.user?.role || 'user'}. Only customer accounts can book stays. Please switch to a customer account.`;
  }
});
const orderedDates = new Rule((c, e) => {
  if (c.checkIn && c.checkOut && stayNights(c.checkIn, c.checkOut) <= 0) {
    e.problem = 'Check-out date must be strictly after check-in date.';
  }
});
const maxLength = new Rule((c, e) => {
  if (stayNights(c.checkIn, c.checkOut) > 14) {
    e.problem = 'Stays cannot exceed 14 nights (StayNest policy). Please select a shorter duration.';
  }
});

const BOOKING_CHAIN = chain(signedIn, customerOnly, orderedDates, maxLength);
export const bookingProblem = (context) => BOOKING_CHAIN.run(context, {}, true).problem ?? null;
