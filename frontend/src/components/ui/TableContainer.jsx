import React from 'react';

/**
 * StayNest TableContainer component
 * Wraps responsive tables in a keyboard-accessible, horizontally scrollable region
 * so wide data sets remain readable on mobile screens (Requirement 8.2 & docs/design-system.md).
 */
export default function TableContainer({
  label = 'Data table',
  children,
  className = '',
}) {
  return (
    <div
      role="region"
      tabIndex={0}
      aria-label={label}
      className={`table-container ${className}`.trim()}
    >
      {children}
    </div>
  );
}
