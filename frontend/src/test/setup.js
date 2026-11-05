import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Node >= 22 ships its own (unusable) localStorage global that shadows jsdom's.
class MemoryStorage {
  #data = new Map();
  get length() { return this.#data.size; }
  key(i) { return [...this.#data.keys()][i] ?? null; }
  getItem(k) { return this.#data.has(k) ? this.#data.get(k) : null; }
  setItem(k, v) { this.#data.set(String(k), String(v)); }
  removeItem(k) { this.#data.delete(k); }
  clear() { this.#data.clear(); }
}
Object.defineProperty(globalThis, 'localStorage', { value: new MemoryStorage(), configurable: true, writable: true });
Object.defineProperty(window, 'localStorage', { value: globalThis.localStorage, configurable: true, writable: true });

if (!window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: false, media: query, addEventListener() {}, removeEventListener() {} });
}

afterEach(() => {
  cleanup();
  localStorage.clear();
});
