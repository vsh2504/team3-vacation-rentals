import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

async function load(key) {
  vi.resetModules();
  vi.stubEnv('VITE_GOOGLE_MAPS_KEY', key);
  return import('./googleMaps.js');
}
const scripts = () => [...document.head.querySelectorAll('script')];

beforeEach(() => { delete window.google; scripts().forEach(s => s.remove()); });
afterEach(() => vi.unstubAllEnvs());

describe('googleMaps loader', () => {
  it('resolves null without an API key', async () => {
    const mod = await load('');
    expect(mod.hasGoogleMaps).toBe(false);
    expect(await mod.loadGoogleMaps()).toBeNull();
    expect(scripts()).toHaveLength(0);
  });

  it('injects the script once, imports libraries and shares the promise', async () => {
    const mod = await load('abc 123');
    expect(mod.hasGoogleMaps).toBe(true);
    const importLibrary = vi.fn().mockResolvedValue({});
    const first = mod.loadGoogleMaps();
    expect(mod.loadGoogleMaps()).toBe(first);
    expect(scripts()).toHaveLength(1);
    expect(scripts()[0].src).toContain('key=abc%20123');
    window.google = { maps: { importLibrary } };
    scripts()[0].onload();
    expect(await first).toBe(window.google);
    expect(importLibrary.mock.calls.map(c => c[0])).toEqual(['maps', 'marker', 'places']);
  });

  it('skips injecting when the API is already present', async () => {
    const mod = await load('k');
    window.google = { maps: { importLibrary: vi.fn().mockResolvedValue({}) } };
    expect(await mod.loadGoogleMaps()).toBe(window.google);
    expect(scripts()).toHaveLength(0);
  });

  it('resolves null on a load error and allows a retry', async () => {
    const mod = await load('k');
    const failed = mod.loadGoogleMaps();
    scripts()[0].onerror();
    expect(await failed).toBeNull();
    const retry = mod.loadGoogleMaps();
    expect(scripts()).toHaveLength(2);
    window.google = { maps: { importLibrary: vi.fn().mockResolvedValue({}) } };
    scripts()[1].onload();
    expect(await retry).toBe(window.google);
  });
});
