// Pattern gate: each pattern module must declare its pattern, and the pages
// must actually use the shared pattern modules (not keep private copies).
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const src = (path) => readFileSync(join(process.cwd(), 'src', path), 'utf8');

const DECLARED = {
  'api/client.js': ['Factory', 'Singleton', 'Facade', 'Decorator', 'Adapter'],
  'state/createStore.js': ['Observer'],
  'state/authStore.js': ['Observer', 'Memento', 'Singleton'],
  'services/navigation.js': ['Strategy'],
  'validation/chain.js': ['Chain of Responsibility'],
  'validation/search.js': ['Chain of Responsibility'],
  'validation/auth.js': ['Chain of Responsibility'],
  'validation/booking.js': ['Chain of Responsibility'],
  'components/RoleGuard.jsx': ['Protection Proxy'],
  'components/ErrorBoundary.jsx': ['State'],
};

describe('declared patterns', () => {
  it.each(Object.entries(DECLARED))('%s names its pattern(s)', (file, patterns) => {
    const text = src(file);
    patterns.forEach(name => expect(text).toContain(name));
  });
});

describe('wiring', () => {
  it.each([
    ['App.jsx', ["from './state/authStore.js'", "from './services/navigation.js'"]],
    ['pages/AdminPage.jsx', ["from '../components/RoleGuard.jsx'"]],
    ['pages/AnalyticsPage.jsx', ["from '../components/RoleGuard.jsx'"]],
    ['pages/SearchPage.jsx', ["from '../validation/search.js'"]],
    ['pages/AuthPage.jsx', ["from '../validation/auth.js'"]],
    ['components/BookingForm.jsx', ["from '../validation/booking.js'"]],
  ])('%s uses the shared modules', (file, imports) => {
    const text = src(file);
    imports.forEach(line => expect(text).toContain(line));
  });
});
