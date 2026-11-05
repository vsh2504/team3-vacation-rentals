import React from 'react';

/**
 * StayNest Spinner component
 * Accessible loading indicator.
 */
export default function Spinner({
  size = 'md',
  label = 'Loading…',
  className = '',
}) {
  return (
    <span
      role="status"
      className={`spinner spinner-${size} ${className}`.trim()}
      aria-label={label}
    >
      <span className="sn-visually-hidden">{label}</span>
    </span>
  );
}
