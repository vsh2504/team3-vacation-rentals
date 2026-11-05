// Patterns: Observer (subscribers re-render on login/logout), Memento (the
// session is snapshotted to storage and restored on the next page load) and
// Singleton (`authStore` is the one shared session).
import { useCallback, useSyncExternalStore } from 'react';
import { createStore } from './createStore.js';

export const AUTH_KEY = 'staynest_auth';

export function loadAuth(storage) {
  try {
    return JSON.parse(storage.getItem(AUTH_KEY) || 'null');
  } catch {
    return null;
  }
}

export function createAuthStore(storage) {
  const store = createStore(loadAuth(storage));
  return {
    getState: store.getState,
    subscribe: store.subscribe,
    login(token, user) {
      const session = { token, user };
      try { storage.setItem(AUTH_KEY, JSON.stringify(session)); } catch { /* storage unavailable */ }
      store.setState(session);
    },
    logout() {
      try { storage.removeItem(AUTH_KEY); } catch { /* storage unavailable */ }
      store.setState(null);
    },
  };
}

export const authStore = createAuthStore(localStorage);

export function useAuth() {
  const auth = useSyncExternalStore(authStore.subscribe, authStore.getState);
  const login = useCallback((token, user) => authStore.login(token, user), []);
  const logout = useCallback(() => authStore.logout(), []);
  return { auth, login, logout };
}
