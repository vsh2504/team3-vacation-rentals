// Sign-in / register validation as a Chain of Responsibility (see chain.js).
import { Rule, chain } from './chain.js';

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const email = new Rule((f, e) => {
  if (!f.email.trim()) e.email = 'Email address is required.';
  else if (!EMAIL.test(f.email.trim())) e.email = 'Please enter a valid email address.';
});
const password = new Rule((f, e) => {
  if (!f.password) e.password = 'Password is required.';
  else if (f.password.length < 8) e.password = 'Password must be at least 8 characters.';
});
const registration = new Rule((f, e) => {
  if (f.mode !== 'register') return;
  if (!f.fullName.trim()) e.fullName = 'Full name is required.';
  if (f.role !== 'CUSTOMER' && f.role !== 'HOST') e.role = 'Please select a valid account role.';
});

const AUTH_CHAIN = chain(email, password, registration);
export const validateAuth = (form) => AUTH_CHAIN.run(form, {});
