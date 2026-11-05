import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ErrorBoundary from './ErrorBoundary.jsx';

let shouldThrow;
let message;
const Bomb = () => {
  if (shouldThrow) throw new Error(message);
  return <p>fine</p>;
};

describe('ErrorBoundary (State)', () => {
  beforeEach(() => { shouldThrow = true; message = 'kaboom'; vi.spyOn(console, 'error').mockImplementation(() => {}); });
  afterEach(() => vi.restoreAllMocks());

  it('renders children when nothing fails', () => {
    shouldThrow = false;
    render(<ErrorBoundary><Bomb /></ErrorBoundary>);
    expect(screen.getByText('fine')).toBeInTheDocument();
  });

  it('shows the error and recovers via "Try again"', () => {
    render(<ErrorBoundary><Bomb /></ErrorBoundary>);
    expect(screen.getByText('Something went wrong loading this view')).toBeInTheDocument();
    expect(screen.getByText('kaboom')).toBeInTheDocument();
    shouldThrow = false;
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(screen.getByText('fine')).toBeInTheDocument();
  });

  it('falls back to a generic message when the error has none', () => {
    message = '';
    render(<ErrorBoundary><Bomb /></ErrorBoundary>);
    expect(screen.getByText(/unexpected application error/)).toBeInTheDocument();
  });
});
