import React from 'react';

/**
 * StayNest Alert component
 * Accessible feedback panel for validation, errors, success, and notices.
 *
 * Variants:
 * - error: role="alert", aria-live="assertive" (for failures / validation errors)
 * - success: role="status", aria-live="polite" (for confirmed actions)
 * - warning: role="status", aria-live="polite" (for warnings)
 * - info: role="status", aria-live="polite" (for informational notices)
 */
export default function Alert({
  variant = 'info',
  title,
  children,
  onDismiss,
  className = '',
  id,
}) {
  const isAssertive = variant === 'error';
  const role = isAssertive ? 'alert' : 'status';
  const live = isAssertive ? 'assertive' : 'polite';

  const defaultIcons = {
    error: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
    ),
    success: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
        <polyline points="22 4 12 14.01 9 11.01"></polyline>
      </svg>
    ),
    warning: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
        <line x1="12" y1="9" x2="12" y2="13"></line>
        <line x1="12" y1="17" x2="12.01" y2="17"></line>
      </svg>
    ),
    info: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="16" x2="12" y2="12"></line>
        <line x1="12" y1="8" x2="12.01" y2="8"></line>
      </svg>
    ),
  };

  return (
    <div
      id={id}
      role={role}
      aria-live={live}
      className={`alert alert-${variant} ${className}`.trim()}
    >
      <div className="alert-icon">
        {defaultIcons[variant] || defaultIcons.info}
      </div>
      <div className="alert-content">
        {title && <strong className="alert-title">{title}</strong>}
        <div className="alert-message">{children}</div>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="alert-dismiss"
          aria-label="Dismiss message"
        >
          <span aria-hidden="true">&times;</span>
        </button>
      )}
    </div>
  );
}
