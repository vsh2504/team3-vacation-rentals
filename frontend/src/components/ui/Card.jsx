import React from 'react';

/**
 * StayNest Card component
 * Surface container with tokens-aligned border, radius, and elevation.
 */
export default function Card({
  as: Component = 'article',
  elevation = 'rest',
  children,
  className = '',
  ...props
}) {
  const elevationClass = elevation === 'raised' ? 'card-raised' : 'card-rest';
  return (
    <Component className={`page-card ${elevationClass} ${className}`.trim()} {...props}>
      {children}
    </Component>
  );
}
