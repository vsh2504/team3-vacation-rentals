import { useCallback, useEffect, useState } from 'react';

// Light/dark preference. index.html sets data-theme before first paint; this
// hook keeps React in sync, persists the choice, and follows the system
// setting until the person picks one explicitly.
const KEY = 'staynest-theme';
const read = () => (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');

export function useTheme() {
  const [theme, setTheme] = useState(read);

  const apply = useCallback((next, { save }) => {
    const root = document.documentElement;
    // Fade colours for a moment so the switch is a transition, not a jump.
    root.classList.add('theme-fade');
    root.dataset.theme = next;
    window.setTimeout(() => root.classList.remove('theme-fade'), 450);
    if (save) { try { localStorage.setItem(KEY, next); } catch { /* storage unavailable */ } }
    setTheme(next);
  }, []);

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = e => {
      let saved = null;
      try { saved = localStorage.getItem(KEY); } catch { /* storage unavailable */ }
      if (saved !== 'light' && saved !== 'dark') apply(e.matches ? 'dark' : 'light', { save: false });
    };
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, [apply]);

  const toggle = useCallback(() => apply(read() === 'dark' ? 'light' : 'dark', { save: true }), [apply]);
  return { theme, toggle };
}
