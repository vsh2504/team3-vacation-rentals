import React from 'react';

/**
 * StayNest Badge component
 * Displays status indicators with accessible contrast and paired text labels.
 *
 * Variants:
 * - primary: Tide teal tint (for brand / info tags)
 * - accent: Marigold with ink text (for ratings, "Booked today")
 * - success: Green tint (Approved, Confirmed)
 * - warning: Amber tint (Pending approval)
 * - danger: Red tint (Rejected, Cancelled, Removed)
 * - neutral: Soft gray (Roles, general metadata)
 */
export default function Badge({
  variant = 'neutral',
  children,
  className = '',
  icon = null,
  title,
}) {
  const variantClass = `badge badge-${variant}`;
  return (
    <span className={`${variantClass} ${className}`.trim()} title={title}>
      {icon && <span className="badge-icon" aria-hidden="true">{icon}</span>}
      <span className="badge-text">{children}</span>
    </span>
  );
}
