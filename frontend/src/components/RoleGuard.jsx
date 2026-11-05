// Pattern: Protection Proxy. Stands in front of a page and only lets the real
// content render when the session holds an allowed role; otherwise it shows
// the page's own "logged out" or "not allowed" message.
export default function RoleGuard({ auth, roles, loggedOut, denied, children }) {
  if (!auth) return loggedOut;
  if (!roles.includes(auth.user?.role)) return denied;
  return children;
}
