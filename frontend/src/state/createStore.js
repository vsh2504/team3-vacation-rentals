// Pattern: Observer. A tiny subject: components (observers) subscribe and are
// told whenever the state changes; the store never knows who is listening.
export function createStore(initial) {
  let state = initial;
  const observers = new Set();
  return {
    getState: () => state,
    setState(next) {
      if (Object.is(next, state)) return;
      state = next;
      observers.forEach((notify) => {
        try { notify(state); } catch { /* one bad observer must not block the rest */ }
      });
    },
    subscribe(observer) {
      observers.add(observer);
      return () => observers.delete(observer);
    },
  };
}
