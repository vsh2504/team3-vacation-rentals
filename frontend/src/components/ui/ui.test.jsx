import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Alert, Badge, Button, Card, Spinner, TableContainer } from './index.js';

describe('Alert', () => {
  it('errors are assertive alerts and can be dismissed', () => {
    const onDismiss = vi.fn();
    render(<Alert variant="error" title="Oops" onDismiss={onDismiss} id="a1">Bad</Alert>);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveAttribute('aria-live', 'assertive');
    expect(alert).toHaveClass('alert-error');
    expect(screen.getByText('Oops')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Dismiss message'));
    expect(onDismiss).toHaveBeenCalled();
  });
  it.each(['success', 'warning', 'info'])('%s is a polite status', (variant) => {
    render(<Alert variant={variant}>msg</Alert>);
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
    expect(screen.queryByLabelText('Dismiss message')).toBeNull();
  });
  it('defaults to info and falls back to the info icon for unknown variants', () => {
    const { container, rerender } = render(<Alert>hello</Alert>);
    expect(container.firstChild).toHaveClass('alert-info');
    rerender(<Alert variant="mystery" className="extra">hello</Alert>);
    expect(container.querySelector('.alert-icon svg')).not.toBeNull();
    expect(container.firstChild).toHaveClass('extra');
  });
});

describe('Button', () => {
  it('renders children, icon and handles clicks', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick} icon="★" variant="danger" size="sm" className="x">Go</Button>);
    const button = screen.getByRole('button', { name: /Go/ });
    expect(button).toHaveClass('btn-danger', 'btn-sm', 'x');
    expect(screen.getByText('★')).toBeInTheDocument();
    fireEvent.click(button);
    expect(onClick).toHaveBeenCalled();
  });
  it('shows a spinner and disables itself while loading', () => {
    render(<Button isLoading loadingText="Saving…" icon="★">Save</Button>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(screen.getAllByText('Saving…').length).toBeGreaterThan(0);
    expect(screen.queryByText('★')).toBeNull();
  });
  it('uses a default loading label and keeps children when no loading text', () => {
    const { rerender } = render(<Button isLoading>Save</Button>);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Processing…');
    expect(screen.getByRole('button')).toHaveTextContent('Save');
    rerender(<Button disabled type="submit">Save</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByRole('button')).toHaveAttribute('type', 'submit');
  });
});

describe('Badge, Spinner, Card, TableContainer', () => {
  it('Badge renders variant, optional icon and title', () => {
    const { rerender } = render(<Badge>Role</Badge>);
    expect(screen.getByText('Role').parentElement).toHaveClass('badge-neutral');
    rerender(<Badge variant="success" icon="✓" title="ok" className="z">Done</Badge>);
    expect(screen.getByText('✓')).toBeInTheDocument();
    expect(screen.getByTitle('ok')).toHaveClass('badge-success', 'z');
  });
  it('Spinner is an accessible status', () => {
    const { rerender } = render(<Spinner />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Loading…');
    rerender(<Spinner size="sm" label="Busy" className="c" />);
    expect(screen.getByRole('status')).toHaveClass('spinner-sm', 'c');
  });
  it('Card chooses its element and elevation', () => {
    const { container, rerender } = render(<Card>body</Card>);
    expect(container.firstChild.tagName).toBe('ARTICLE');
    expect(container.firstChild).toHaveClass('card-rest');
    rerender(<Card as="section" elevation="raised" className="k" data-x="1">body</Card>);
    expect(container.firstChild.tagName).toBe('SECTION');
    expect(container.firstChild).toHaveClass('card-raised', 'k');
  });
  it('TableContainer is a focusable labelled region', () => {
    const { rerender } = render(<TableContainer>t</TableContainer>);
    expect(screen.getByRole('region', { name: 'Data table' })).toHaveAttribute('tabindex', '0');
    rerender(<TableContainer label="Rows" className="w">t</TableContainer>);
    expect(screen.getByRole('region', { name: 'Rows' })).toHaveClass('w');
  });
});
