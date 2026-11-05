// Search-form validation as a Chain of Responsibility (see chain.js).
import { Rule, chain } from './chain.js';

const DAY = 86400000;
export const nightsBetween = (a, b) => Math.round((new Date(b) - new Date(a)) / DAY);

const guests = new Rule((f, e) => {
  if (!(Number(f.guests) >= 1)) e.guests = 'Enter at least 1 guest.';
});
const datePair = new Rule((f, e) => {
  if (f.checkIn && !f.checkOut) e.checkOut = 'Choose a check-out date.';
  if (f.checkOut && !f.checkIn) e.checkIn = 'Choose a check-in date.';
});
const dateRange = new Rule((f, e) => {
  if (!(f.checkIn && f.checkOut)) return;
  const n = nightsBetween(f.checkIn, f.checkOut);
  if (n <= 0) e.checkOut = 'Check-out must be after check-in.';
  else if (n > 14) e.checkOut = `Stays are limited to 14 nights (you chose ${n}).`;
});

const SEARCH_CHAIN = chain(guests, datePair, dateRange);
export const validateSearch = (form) => SEARCH_CHAIN.run(form, {});
