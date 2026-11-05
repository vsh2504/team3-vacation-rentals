import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useTheme } from './theme.js';
import ThemeToggle from './components/ThemeToggle.jsx';

let listeners;
let media;
beforeEach(() => {
  vi.useFakeTimers();
  listeners = new Set();
  media = {
    addEventListener: (_, fn) => listeners.add(fn),
    removeEventListener: (_, fn) => listeners.delete(fn),
  };
  window.matchMedia = vi.fn(() => media);
  delete document.documentElement.dataset.theme;
});
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

const systemChange = (matches) => act(() => listeners.forEach(fn => fn({ matches })));

describe('useTheme', () => {
  it('starts from the document theme and toggles, persists and fades', () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe('light');
    act(() => result.current.toggle());
    expect(result.current.theme).toBe('dark');
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(localStorage.getItem('staynest-theme')).toBe('dark');
    expect(document.documentElement).toHaveClass('theme-fade');
    act(() => vi.advanceTimersByTime(450));
    expect(document.documentElement).not.toHaveClass('theme-fade');
    act(() => result.current.toggle());
    expect(result.current.theme).toBe('light');
  });

  it('reads an initial dark theme', () => {
    document.documentElement.dataset.theme = 'dark';
    expect(renderHook(() => useTheme()).result.current.theme).toBe('dark');
  });

  it('follows the system theme until the person chooses one', () => {
    const { result } = renderHook(() => useTheme());
    systemChange(true);
    expect(result.current.theme).toBe('dark');
    expect(localStorage.getItem('staynest-theme')).toBeNull();
    systemChange(false);
    expect(result.current.theme).toBe('light');
    localStorage.setItem('staynest-theme', 'dark');
    systemChange(true);
    expect(result.current.theme).toBe('light');
  });

  it('copes with unavailable storage', () => {
    vi.spyOn(localStorage, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
    vi.spyOn(localStorage, 'setItem').mockImplementation(() => { throw new Error('blocked'); });
    const { result } = renderHook(() => useTheme());
    systemChange(true);
    expect(result.current.theme).toBe('dark');
    act(() => result.current.toggle());
    expect(result.current.theme).toBe('light');
  });

  it('stops listening when unmounted', () => {
    const { unmount } = renderHook(() => useTheme());
    expect(listeners.size).toBe(1);
    unmount();
    expect(listeners.size).toBe(0);
  });
});

describe('ThemeToggle', () => {
  it('labels and flips with the theme', () => {
    render(<ThemeToggle />);
    const button = screen.getByRole('button', { name: 'Switch to dark mode' });
    expect(button).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(button);
    expect(screen.getByRole('button', { name: 'Switch to light mode' })).toHaveAttribute('aria-pressed', 'true');
  });
});
