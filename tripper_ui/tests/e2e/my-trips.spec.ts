import { expect, test } from '@playwright/test';

test('user creates a trip and finds it in My Trips as creator', async ({ page }) => {
  await page.addInitScript(() => {
    let googleCallback: (response: { credential: string }) => void;
    window.google = { accounts: { id: {
      initialize(options) { googleCallback = options.callback; },
      renderButton(element) {
        const button = document.createElement('button');
        button.textContent = 'Sign in with Google';
        button.addEventListener('click', () => {
          googleCallback({ credential: 'e2e-google-credential' });
        });
        element.appendChild(button);
      },
    } } };
  });
  await page.goto('/tripper/my-trips');
  await page.getByRole('button', { name: 'Sign in with Google' }).click();

  await expect(page.getByRole('heading', { name: 'My Trips' })).toBeVisible();
  await expect(page.getByText('You have no trips yet.')).toBeVisible();

  await page.getByRole('button', { name: 'Create trip' }).click();
  await page.getByLabel('Trip name').fill('Greek Islands 2027');
  await page.getByLabel('Short name').fill('Greek Islands');
  await page.getByLabel('Destination').fill('Cyclades');
  await page.getByLabel('Description').fill('A week through the Cyclades');
  await page.getByLabel('Timezone').fill('Europe/Athens');
  await page.getByLabel('Latitude').fill('37.4467');
  await page.getByLabel('Longitude').fill('25.3289');
  await page.getByLabel('Start date').fill('2027-06-10');
  await page.getByLabel('End date').fill('2027-06-17');
  await page.getByRole('button', { name: 'Save trip' }).click();

  await expect(page).toHaveURL(/\/tripper\/trips\/[0-9a-f-]+\/edit$/);
  await expect(page.getByRole('heading', { name: 'Plan' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'June 10, 2027' })).toHaveAttribute(
    'aria-current',
    'date',
  );
  await expect(page.getByRole('button', { name: /June \d+, 2027/ })).toHaveCount(8);
  await expect(page.getByText('Not planned yet')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'People' })).toBeVisible();
  await expect(page.locator('.trip-planner__roster-item')).toContainText([
    'E2E TravellerCreator',
  ]);

  await page.goto('/tripper/my-trips');
  const trip = page.getByRole('link', { name: /Greek Islands 2027/ });
  await expect(trip).toContainText('Cyclades');
  await expect(trip).toContainText('Creator');

  await page.getByRole('button', { name: 'Create trip' }).click();
  await page.getByLabel('Trip name').fill('Japan 2028');
  await page.getByLabel('Destination').fill('Tokyo');
  await page.getByLabel('Timezone').fill('Asia/Tokyo');
  await page.getByLabel('Start date').fill('2028-04-01');
  await page.getByLabel('End date').fill('2028-04-03');
  await page.getByRole('button', { name: 'Save trip' }).click();

  await expect(page.getByRole('heading', { name: 'Plan' })).toBeVisible();
  await page.goto('/tripper/my-trips');
  await expect(page.getByRole('link', { name: /Greek Islands 2027/ })).toBeVisible();
  await expect(page.getByRole('link', { name: /Japan 2028/ })).toContainText('Creator');

  await page.reload();
  await expect(page.getByRole('link', { name: /Greek Islands 2027/ })).toContainText('Creator');

  const persistedTrip = page.getByRole('link', { name: /Greek Islands 2027/ });
  await persistedTrip.click();
  await expect(page.getByRole('heading', { name: 'Plan' })).toBeVisible();
  await expect(page.getByText('Not planned yet')).toBeVisible();

  await page.goto('/tripper/my-trips');
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page.getByText('Sign in with Google to see your trips.')).toBeVisible();
});

test('participant guide renders canonical API content without loading legacy JSON', async ({ page }) => {
  const requestedPaths: string[] = [];
  page.on('request', (request) => requestedPaths.push(new URL(request.url()).pathname));
  await page.route('**/api/trips/imported', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        id: '223eb014-ff17-51e7-9507-b956164ff7a4',
        name: 'Los Angeles 2026',
        destination: 'Los Angeles',
        short_name: 'LA Trip 2026',
        description: 'Los Angeles Trip Itinerary',
        timezone: 'America/Los_Angeles',
        location: null,
        start_date: '2026-11-13',
        end_date: '2026-11-13',
        calendar: [{ date: '2026-11-13', day_number: 1, is_planned: true }],
        daily_plans: [{
          date: '2026-11-13',
          day_number: 1,
          title: 'Arrival at Downtown LA',
          summary: 'Land at LAX and settle into Downtown LA.',
          background_image: 'https://example.com/background.jpg',
          stay: {
            name: 'Fashion Loft',
            address: '814 South Spring Street',
            location: null,
            check_in: '16:30:00',
            check_out: null,
            public_listing_url: 'https://example.com/stay',
            booking_platform: 'booking.com',
          },
          timeline: [{
            time: '15:00:00',
            title: 'Arrive at LAX',
            description: 'Pick up the rental car.',
            location: null,
            location_name: null,
          }],
          photos: [{ url: 'https://example.com/photo.jpg', caption: 'Downtown LA skyline' }],
        }],
        roster: [{ display_name: 'E2E Traveller', role: 'creator' }],
      }),
    });
  });

  await page.goto('/tripper/trips/imported');

  await expect(page.getByRole('heading', { name: 'Arrival at Downtown LA' })).toBeVisible();
  await expect(page.getByText('Arrive at LAX')).toBeVisible();
  await expect(page.getByText('Fashion Loft')).toBeVisible();
  await expect(page.getByAltText('Downtown LA skyline')).toBeVisible();
  expect(requestedPaths).not.toContain('/tripper/data/trip.json');
  expect(requestedPaths).not.toContain('/tripper/data/days.json');
});
