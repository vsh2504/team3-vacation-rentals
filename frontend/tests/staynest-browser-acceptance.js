async page => {
  // The runner opens the browser at the acceptance URL before running this
  // script, so derive the origin from the live page instead of relying on
  // Node globals that the Playwright CLI sandbox does not expose.
  const baseURL = new URL(page.url()).origin;
  const results = [];
  const assert = (condition, message) => {
    if (!condition) throw new Error(message);
  };
  const visible = async (locator, message) => {
    await locator.waitFor({ state: 'visible', timeout: 8000 });
    assert(await locator.isVisible(), message);
  };
  const respond = (route, data, status = 200) => route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(status >= 400
      ? { success: false, data: null, error: { code: 'TEST_ERROR', message: String(data) } }
      : { success: true, data, error: null }),
  });

  const listing = {
    id: 7,
    host_id: 10,
    title: 'Harbor Loft',
    description: 'A complete waterfront home used by the acceptance suite.',
    address: '7 Harbor Way',
    city: 'San Jose',
    state: 'CA',
    zip: '95110',
    lat: 37.3382,
    lng: -121.8863,
    price_per_night: '180.00',
    nightly_price: '180.00',
    total_cost: '540.00',
    nights: 3,
    max_guests: 4,
    bedrooms: 2,
    bathrooms: 1,
    amenities: ['WiFi', 'Kitchen', 'Parking'],
    available_times: 'Daily check-in 3pm and check-out 11am',
    operating_start_time: '08:00',
    operating_end_time: '22:00',
    check_in_time: '15:00',
    check_out_time: '11:00',
    status: 'APPROVED',
    photos: [],
    videos: [],
    average_rating: 4.8,
    review_count: 1,
    reviews: [{ id: 1, rating: 5, comment: 'Walkable and quiet.' }],
    booked_today: 2,
    available: true,
    is_available: true,
    availability: { requested: true, available: true, nights: 3, total_cost: '540.00' },
    listing_url: '/listings/7',
    map_url: 'https://www.openstreetmap.org/?mlat=37.3382&mlon=-121.8863',
  };
  const unavailableListing = {
    ...listing,
    id: 8,
    title: 'Unavailable Cottage',
    lat: 37.36,
    lng: -121.9,
    price_per_night: '95.00',
    nightly_price: '95.00',
    total_cost: '285.00',
    available: false,
    is_available: false,
    availability: { requested: false, available: false, nights: 3, total_cost: '285.00' },
    listing_url: '/listings/8',
  };
  let hostListings = [{
    ...listing,
    id: 41,
    title: 'Host Draft',
    status: 'PENDING_APPROVAL',
    available: false,
    is_available: false,
    host_contact_name: 'Holly Host',
    host_contact_email: 'host@staynest.test',
    host_contact_phone: '408-555-0101',
  }];
  let moderationListings = [{
    ...hostListings[0],
    host: { id: 10, full_name: 'Holly Host', email: 'host@staynest.test', phone: '408-555-0101' },
    searchable: false,
    photo_count: 0,
    video_count: 0,
    completeness: { complete: true, score: 100, missing: [], checks: {} },
  }];
  let bookingPayload = null;
  let hostUpdatePayload = null;
  let reviewPayload = null;
  let cancelledBookingId = null;
  let analyticsRequest = '';
  const upcomingBooking = {
    id: 89,
    listing_id: 7,
    customer_id: 20,
    check_in: '2027-04-10',
    check_out: '2027-04-13',
    check_in_time: '15:00',
    check_out_time: '11:00',
    guests: 2,
    total_price: '540.00',
    status: 'CONFIRMED',
    stay_state: 'upcoming',
    booked_date: '2026-01-01',
    location: {
      address: listing.address,
      city: listing.city,
      state: listing.state,
      zip: listing.zip,
      lat: listing.lat,
      lng: listing.lng,
      map_url: listing.map_url,
    },
    listing: { id: 7, title: listing.title, photos: [], url: '/listings/7' },
  };
  const completedBooking = {
    id: 88,
    listing_id: 7,
    customer_id: 20,
    check_in: '2026-01-01',
    check_out: '2026-01-03',
    check_in_time: '15:00',
    check_out_time: '11:00',
    guests: 2,
    total_price: '360.00',
    status: 'COMPLETED',
    stay_state: 'past',
    booked_date: '2026-01-01',
    location: {
      address: listing.address,
      city: listing.city,
      state: listing.state,
      zip: listing.zip,
      lat: listing.lat,
      lng: listing.lng,
      map_url: listing.map_url,
    },
    listing: { id: 7, title: listing.title, photos: [], url: '/listings/7' },
  };

  await page.route('https://tile.openstreetmap.org/**', route => route.abort());
  // Match only the application API prefix. A bare "**/api/**" glob also
  // matches Vite's own module URL /src/api/client.js and would replace the
  // client module with JSON, breaking the app under test.
  await page.route(`${baseURL}/api/**`, async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    if (path === '/api/listings/search') return respond(route, [listing, unavailableListing]);
    if (path === '/api/geocode') {
      return respond(route, {
        display_name: '7 Harbor Way, San Jose, CA 95110',
        city: 'San Jose',
        state: 'CA',
        zip: '95110',
        lat: 37.3382,
        lng: -121.8863,
        provider: 'nominatim',
      });
    }
    if (path === '/api/listings/7/reviews') {
      return respond(route, { listing_id: 7, average_rating: 4.8, count: 1, reviews: listing.reviews });
    }
    if (path === '/api/listings/7' && method === 'GET') return respond(route, listing);
    if (path === '/api/bookings' && method === 'POST') {
      bookingPayload = request.postDataJSON();
      return respond(route, {
        id: 501,
        ...bookingPayload,
        total_price: '540.00',
        status: 'CONFIRMED',
      });
    }
    if (path === '/api/host/listings' && method === 'GET') return respond(route, hostListings);
    if (path === '/api/listings/41' && method === 'PUT') {
      hostUpdatePayload = request.postDataJSON();
      hostListings = [{ ...hostListings[0], ...hostUpdatePayload, status: 'PENDING_APPROVAL' }];
      return respond(route, hostListings[0]);
    }
    if (path === '/api/admin/listings' && method === 'GET') {
      const status = url.searchParams.get('status');
      return respond(route, status
        ? moderationListings.filter(item => item.status === status)
        : moderationListings);
    }
    if (path === '/api/admin/listings/41/approve' && method === 'POST') {
      moderationListings = [{ ...moderationListings[0], status: 'APPROVED', searchable: true }];
      return respond(route, moderationListings[0]);
    }
    if (path === '/api/bookings/me' && method === 'GET') {
      return respond(route, cancelledBookingId === upcomingBooking.id
        ? [{ ...upcomingBooking, status: 'CANCELLED', stay_state: 'cancelled' }, completedBooking]
        : [upcomingBooking, completedBooking]);
    }
    if (path === '/api/bookings/89/cancel' && method === 'POST') {
      cancelledBookingId = 89;
      return respond(route, { ...upcomingBooking, status: 'CANCELLED', stay_state: 'cancelled' });
    }
    if (path === '/api/host/analytics' && method === 'GET') {
      const days = Number(url.searchParams.get('days') || 30);
      const factor = days / 30;
      analyticsRequest = `host:${url.search}`;
      return respond(route, {
        period_days: days,
        total_rentals: factor,
        total_bookings: 2 * factor,
        total_revenue: (540 * factor).toFixed(2),
        by_zip: [{ zip: '95110', rentals: factor, bookings: 2 * factor,
          revenue: (540 * factor).toFixed(2) }],
      });
    }
    if (path === '/api/admin/analytics' && method === 'GET') {
      const days = Number(url.searchParams.get('days') || 30);
      const zip = url.searchParams.get('zip');
      const factor = days / 30;
      const filtered = zip === '95110';
      analyticsRequest = `admin:${url.search}`;
      return respond(route, {
        period_days: days,
        total_rentals: (filtered ? 2 : 3) * factor,
        total_bookings: (filtered ? 3 : 5) * factor,
        total_revenue: ((filtered ? 750 : 1250) * factor).toFixed(2),
        by_zip: filtered
          ? [{ zip: '95110', rentals: 2 * factor, bookings: 3 * factor,
              revenue: (750 * factor).toFixed(2) }]
          : [
              { zip: '95110', rentals: 2 * factor, bookings: 3 * factor,
                revenue: (750 * factor).toFixed(2) },
              { zip: '94043', rentals: factor, bookings: 2 * factor,
                revenue: (500 * factor).toFixed(2) },
            ],
      });
    }
    if (path === '/api/reviews' && method === 'POST') {
      reviewPayload = request.postDataJSON();
      return respond(route, { id: 900, listing_id: 7, customer_id: 20, ...reviewPayload });
    }
    return respond(route, `Unhandled mocked request: ${method} ${path}`, 500);
  });

  const authenticate = async (role, email) => {
    await page.goto(baseURL);
    await page.evaluate(({ role, email }) => {
      localStorage.setItem('staynest_auth', JSON.stringify({
        token: `test-${role.toLowerCase()}-token`,
        user: { id: role === 'CUSTOMER' ? 20 : 10, email, role },
      }));
    }, { role, email });
    await page.reload();
  };

  await authenticate('CUSTOMER', 'customer@staynest.test');
  await visible(page.getByRole('heading', { name: 'Find a stay' }), 'search page did not render');
  await page.getByLabel('Check-in date').fill('2027-03-01');
  await page.getByLabel('Check-out date').fill('2027-03-04');
  await page.getByLabel('Guests').fill('2');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await visible(page.getByRole('link', { name: 'Harbor Loft', exact: true }).first(), 'search result missing');
  await visible(page.getByText('$540 total for 3 nights'), 'total price is absent from the search result');
  const unavailableAction = page.getByRole('button', { name: 'Unavailable', exact: true });
  await visible(unavailableAction, 'unavailable listing has no disabled action');
  assert(await unavailableAction.isDisabled(), 'unavailable listing booking action is still enabled');
  await page.getByLabel('Address').fill('7 Harbor Way, San Jose');
  await page.getByRole('button', { name: 'Look up', exact: true }).click();
  await page.getByRole('option', { name: '7 Harbor Way, San Jose, CA 95110' }).click();
  assert(await page.getByLabel('City').inputValue() === 'San Jose', 'geocode did not fill city');
  assert(await page.getByLabel('ZIP').inputValue() === '95110', 'geocode did not fill ZIP');
  results.push('unavailable action and address geocoding');
  await page.getByRole('button', { name: 'Map', exact: true }).click();
  await page.getByRole('button', { name: /Marker 1: Harbor Loft/ }).click();
  await visible(page.getByRole('link', { name: 'Open in OpenStreetMap' }), 'OSM interaction link missing');
  results.push('customer search and map interaction');

  await page.getByRole('button', { name: 'List', exact: true }).click();
  await page.getByRole('link', { name: 'Harbor Loft', exact: true }).first().click();
  await visible(page.getByRole('heading', { name: 'Reserve this stay' }), 'booking form missing');
  await page.getByRole('button', { name: 'Book Now' }).click();
  await visible(page.getByRole('heading', { name: 'Booking Confirmed!' }), 'booking confirmation missing');
  assert(bookingPayload?.listing_id === 7 && bookingPayload?.guests === 2,
    'booking request did not preserve listing and guest count');
  results.push('customer booking');

  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(baseURL);
  const navToggle = page.getByRole('button', { name: 'Toggle navigation menu' });
  await visible(navToggle, 'mobile navigation toggle missing');
  await navToggle.click();
  assert(await navToggle.getAttribute('aria-expanded') === 'true', 'mobile navigation did not expand');
  const overflows = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  assert(!overflows, 'mobile page has horizontal overflow');
  results.push('responsive mobile navigation and layout');
  await page.setViewportSize({ width: 1280, height: 900 });

  await authenticate('HOST', 'host@staynest.test');
  await page.goto(`${baseURL}/host`);
  await visible(page.getByRole('heading', { name: 'Host Management Portal' }), 'host portal missing');
  await visible(page.getByText('PENDING APPROVAL').first(), 'host moderation status missing');
  await page.getByRole('button', { name: 'Edit Listing' }).click();
  await page.getByLabel('Property Title *').fill('Updated Host Draft');
  await page.getByRole('button', { name: 'Save Changes & Re-submit' }).click();
  await visible(page.getByText(/Listing #41 updated successfully/), 'host update success missing');
  assert(hostUpdatePayload?.title === 'Updated Host Draft', 'host edit payload was not submitted');
  results.push('host listing management');

  await page.goto(`${baseURL}/analytics`);
  await visible(page.getByRole('heading', { name: 'Host analytics' }), 'host analytics missing');
  await visible(page.getByText('Your listings only'), 'host analytics scope label missing');
  await visible(page.getByText('$540.00').first(), 'host analytics revenue missing');
  await page.getByRole('button', { name: '90 days', exact: true }).click();
  await visible(page.getByText('$1,620.00').first(), 'host 90-day revenue did not update');
  assert(analyticsRequest.startsWith('host:') && analyticsRequest.includes('days=90'),
    'host analytics did not request the 90-day period');
  results.push('host analytics period scope');

  await authenticate('ADMIN', 'admin@staynest.test');
  await page.goto(`${baseURL}/admin`);
  await visible(page.getByRole('heading', { name: 'Moderation queue' }), 'admin queue missing');
  await page.getByRole('button', { name: 'Approve Host Draft' }).click();
  await visible(page.getByText(/approved — it now appears in search/), 'admin approval feedback missing');
  assert(moderationListings[0].status === 'APPROVED' && moderationListings[0].searchable,
    'admin approval did not update moderation/search state');
  results.push('admin approval');

  await page.goto(`${baseURL}/analytics`);
  await visible(page.getByRole('heading', { name: 'Platform analytics' }), 'platform analytics missing');
  await visible(page.getByText('All listings'), 'platform analytics scope label missing');
  await visible(page.getByText('$1,250.00').first(), 'platform analytics revenue missing');
  await page.getByLabel('ZIP filter').fill('95110');
  await page.getByRole('button', { name: 'Apply', exact: true }).click();
  await visible(page.getByText('ZIP 95110'), 'ZIP filter was not reflected in the dashboard');
  await visible(page.getByText('$750.00').first(), 'ZIP-filtered totals are inconsistent');
  assert(analyticsRequest.startsWith('admin:') && analyticsRequest.includes('zip=95110'),
    'admin analytics did not request the ZIP filter');
  results.push('admin platform analytics and ZIP filter');

  await authenticate('CUSTOMER', 'customer@staynest.test');
  await page.goto(`${baseURL}/bookings`);
  await visible(page.getByRole('heading', { name: 'My Bookings & Stays' }), 'bookings page missing');
  await page.getByRole('button', { name: 'Cancel Booking' }).click();
  await page.getByRole('button', { name: 'Confirm Cancel' }).click();
  await visible(page.getByText(/Booking #89 has been successfully cancelled/), 'cancellation success missing');
  assert(cancelledBookingId === 89, 'cancel request did not target the upcoming booking');
  await visible(page.getByRole('tab', { name: /Cancelled \(1\)/ }), 'cancelled tab count did not update');
  results.push('booking cancellation and cancelled tab');
  await visible(page.getByRole('form', { name: 'Submit review for booking #88' }), 'review form missing');
  await page.getByRole('radio', { name: '4 Stars — Very Good' }).click();
  await page.getByLabel(/Review comment/).fill('Clear role-based review flow.');
  await page.getByRole('button', { name: 'Submit Review' }).click();
  await visible(page.getByText(/Thank you! Your review for booking #88 has been recorded/), 'review success missing');
  assert(reviewPayload?.booking_id === 88 && reviewPayload?.rating === 4,
    'review request did not preserve booking and rating');
  results.push('completed-stay review');

  return `PASS ${results.length} browser acceptance areas: ${results.join('; ')}`;
}
