import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { createStore } from './createStore.js';
import { AUTH_KEY, authStore, createAuthStore, loadAuth, useAuth } from './authStore.js';

describe('createStore (Observer)', () => {
  it('notifies subscribers on change and stops after unsubscribe', () => {
    const store = createStore(1);
    const seen = vi.fn();
    const off = store.subscribe(seen);
    store.setState(2);
    expect(store.getState()).toBe(2);
    expect(seen).toHaveBeenCalledWith(2);
    off();
    store.setState(3);
    expect(seen).toHaveBeenCalledTimes(1);
  });

  it('does not notify when the value is unchanged', () => {
    const store = createStore('a');
    const seen = vi.fn();
    store.subscribe(seen);
    store.setState('a');
    expect(seen).not.toHaveBeenCalled();
  });

  it('keeps notifying others when one subscriber throws', () => {
    const store = createStore(0);
    const later = vi.fn();
    store.subscribe(() => { throw new Error('bad observer'); });
    store.subscribe(later);
    store.setState(1);
    expect(later).toHaveBeenCalledWith(1);
  });
});

describe('auth store (Observer + Memento persistence)', () => {
  const user = { email: 'a@b.co', role: 'HOST' };

  it('restores the saved session, tolerating junk and unavailable storage', () => {
    expect(loadAuth(localStorage)).toBeNull();
    localStorage.setItem(AUTH_KEY, '{"token":"t","user":{"role":"HOST"}}');
    expect(loadAuth(localStorage)).toEqual({ token: 't', user: { role: 'HOST' } });
    localStorage.setItem(AUTH_KEY, '{not json');
    expect(loadAuth(localStorage)).toBeNull();
    expect(loadAuth({ getItem() { throw new Error('blocked'); } })).toBeNull();
  });

  it('login persists and notifies; logout clears', () => {
    const store = createAuthStore(localStorage);
    const seen = vi.fn();
    store.subscribe(seen);
    store.login('tok', user);
    expect(store.getState()).toEqual({ token: 'tok', user });
    expect(JSON.parse(localStorage.getItem(AUTH_KEY))).toEqual({ token: 'tok', user });
    store.logout();
    expect(store.getState()).toBeNull();
    expect(localStorage.getItem(AUTH_KEY)).toBeNull();
    expect(seen).toHaveBeenCalledTimes(2);
  });

  it('survives storage write failures', () => {
    const broken = { getItem: () => null, setItem() { throw new Error('quota'); }, removeItem() { throw new Error('quota'); } };
    const store = createAuthStore(broken);
    store.login('tok', user);
    expect(store.getState().token).toBe('tok');
    store.logout();
    expect(store.getState()).toBeNull();
  });

  it('initialises from storage', () => {
    localStorage.setItem(AUTH_KEY, JSON.stringify({ token: 'old', user }));
    expect(createAuthStore(localStorage).getState().token).toBe('old');
  });

  it('useAuth re-renders subscribers when the shared store changes', () => {
    const { result } = renderHook(() => useAuth());
    expect(result.current.auth).toBeNull();
    act(() => result.current.login('t2', user));
    expect(result.current.auth.user.role).toBe('HOST');
    act(() => result.current.logout());
    expect(result.current.auth).toBeNull();
    expect(authStore.getState()).toBeNull();
  });
});
