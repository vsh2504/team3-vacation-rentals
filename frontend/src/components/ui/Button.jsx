import React from 'react';
import Spinner from './Spinner.jsx';

/**
 * StayNest Button component
 * Accessible button with 44px min-touch target, visible focus halo,
 * and loading / disabled state support.
 *
 * Variants:
 * - primary: Tide teal fill, white text (7.1:1 contrast)
 * - secondary: White fill, strong line border, ink text
 * - danger: Danger outline or fill for destructive actions (cancel / remove)
 * - ghost: Low contrast button for inline actions
 */
export default function Button({
  type = 'button',
  variant = 'primary',
  size = 'md',
  isLoading = false,
  loadingText,
  disabled = false,
  onClick,
  children,
  className = '',
  icon = null,
  ...props
}) {
  const isButtonDisabled = disabled || isLoading;

  return (
    <button
      type={type}
      disabled={isButtonDisabled}
      aria-busy={isLoading ? 'true' : undefined}
      onClick={onClick}
      className={`btn btn-${variant} btn-${size} ${className}`.trim()}
      {...props}
    >
      {isLoading && (
        <Spinner size="sm" label={loadingText || 'Processing…'} className="btn-spinner" />
      )}
      {!isLoading && icon && (
        <span className="btn-icon" aria-hidden="true">{icon}</span>
      )}
      <span>{isLoading && loadingText ? loadingText : children}</span>
    </button>
  );
}
