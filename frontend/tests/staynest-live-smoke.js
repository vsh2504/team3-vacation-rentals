async page => {
  // End-to-end smoke against a running StayNest stack (Vite + FastAPI +
  // PostgreSQL). Unlike staynest-browser-acceptance.js this script does not
  // mock the API, so it verifies that the UI consumes the real contracts.
  const baseURL = new URL(page.url()).origin;
  const results = [];
  const assert = (condition, message) => {
    if (!condition) throw new Error(message);
  };
  const visible = async (locator, message) => {
    await locator.waitFor({ state: 'visible', timeout: 15000 });
    assert(await locator.isVisible(), message);
  };

  const login = async (email, password) => {
    await page.goto(baseURL);
    const session = await page.evaluate(async ({ email, password }) => {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const body = await response.json();
      if (!response.ok || !body?.data?.access_token) {
        throw new Error(body?.error?.message || `login failed (${response.status})`);
      }
      return { token: body.data.access_token, user: body.data.user };
    }, { email, password });
    await page.evaluate(value => {
      localStorage.setItem('staynest_auth', JSON.stringify(value));
    }, session);
    await page.reload();
    return session;
  };

  // Public customer discovery: real search, listing detail, and coordinates.
  // Search does not require a session, so the smoke leaves the seeded
  // development users untouched.
  await page.goto(baseURL);
  await visible(page.getByRole('heading', { name: 'Find a stay' }), 'search page did not render');
  await page.getByLabel('Check-in date').fill('2027-05-01');
  await page.getByLabel('Check-out date').fill('2027-05-04');
  await page.getByLabel('Guests').fill('2');
  await page.getByLabel('City').fill('San Jose');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await visible(page.getByText(/listings? found \(API\)/), 'live search did not use the API');
  const firstResult = page.getByRole('link', { name: /Downtown Loft/ }).first();
  await visible(firstResult, 'live search returned no seed listing');
  await firstResult.click();
  await visible(page.getByRole('heading', { name: /Downtown Loft/ }), 'listing detail did not render');
  await visible(page.getByRole('link', { name: /Open in OpenStreetMap/ }), 'listing map link missing');
  results.push('live customer search, detail and map');

  // Host: real owner-scoped listing management.
  await login('host1@staynest.local', 'password123');
  await page.goto(`${baseURL}/host`);
  await visible(page.getByRole('heading', { name: 'Host Management Portal' }), 'host portal missing');
  await visible(page.getByText('My Listings').first(), 'host listing section missing');
  results.push('live host listings');

  // Admin: real moderation queue and platform analytics.
  await login('admin@staynest.local', 'admin12345');
  await page.goto(`${baseURL}/admin`);
  await visible(page.getByRole('heading', { name: 'Moderation queue' }), 'admin moderation queue missing');
  await visible(page.getByText('PENDING APPROVAL').first(), 'pending seed listings missing');
  await page.goto(`${baseURL}/analytics`);
  await visible(page.getByRole('heading', { name: 'Platform analytics' }), 'platform analytics missing');
  await visible(page.getByText('All listings'), 'platform analytics scope missing');
  await visible(page.getByText('Rentals booked'), 'analytics metrics missing');
  results.push('live admin moderation and analytics');

  // Responsive shell against the live app.
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(baseURL);
  const navToggle = page.getByRole('button', { name: 'Toggle navigation menu' });
  await visible(navToggle, 'mobile navigation toggle missing');
  await navToggle.click();
  assert(await navToggle.getAttribute('aria-expanded') === 'true', 'mobile navigation did not expand');
  const overflows = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  assert(!overflows, 'mobile live page has horizontal overflow');
  results.push('live responsive mobile layout');

  return `PASS ${results.length} live acceptance areas: ${results.join('; ')}`;
}
