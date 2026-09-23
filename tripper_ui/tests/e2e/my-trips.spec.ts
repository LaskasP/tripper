import { expect, test } from '@playwright/test';

function editableTrip() {
  return {
    id: '223eb014-ff17-51e7-9507-b956164ff7a4',
    revision: 1,
    role: 'creator',
    name: 'Island draft',
    destination: 'Cyclades',
    short_name: 'Islands',
    description: '',
    timezone: 'Europe/Athens',
    location: null,
    start_date: '2027-06-10',
    end_date: '2027-06-17',
    destinations: [{
      id: '7468f63b-f89a-4c08-8cb1-d54fdd2b7389',
      name: 'Cyclades',
      timezone: 'Europe/Athens',
      location: null,
      position: 0,
      revision: 1,
    }],
    calendar: [],
    daily_plans: [],
    roster: [{ display_name: 'Editor', role: 'creator' }],
  };
}

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

test('participant guide renders canonical API content', async ({ page }) => {
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
});

test('creator edits Trip details and ordered destinations in the planner', async ({ page }) => {
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
  await page.getByRole('button', { name: 'Create trip' }).click();
  await page.getByLabel('Trip name').fill('Cyclades draft');
  await page.getByLabel('Destination').fill('Cyclades');
  await page.getByLabel('Timezone').fill('Europe/Athens');
  await page.getByLabel('Start date').fill('2027-06-10');
  await page.getByLabel('End date').fill('2027-06-17');
  await page.getByRole('button', { name: 'Save trip' }).click();

  await expect(page.getByRole('tab', { name: 'Publish' })).toBeVisible();
  await page.getByRole('tab', { name: 'Trip details' }).click();
  const tripName = page.getByLabel('Trip name');
  await tripName.fill('');
  await tripName.press('Tab');
  await expect(page.getByRole('alert')).toContainText('Trip name is required.');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(tripName).toBeFocused();
  await tripName.fill('Aegean summer');
  await page.getByLabel('Start date').fill('2027-06-08');
  await page.getByLabel('End date').fill('2027-06-19');
  await page.getByRole('button', { name: 'Add destination' }).click();
  await page.getByLabel('Destination 2 name').fill('Athens');
  await page.getByLabel('Destination 2 timezone').fill('Europe/Athens');
  await page.getByRole('button', { name: 'Move Athens up' }).click();

  await expect(page.getByText('Unsaved preview')).toBeVisible();
  await expect(page.getByTestId('trip-preview')).toContainText('Aegean summer');
  await expect(page.getByTestId('trip-preview')).toContainText('Athens → Cyclades');
  await page.reload();
  await expect(page.getByLabel('Trip name')).toHaveValue('Aegean summer');
  await expect(page.getByTestId('trip-preview')).toContainText('Athens → Cyclades');
  await page.getByRole('tab', { name: 'Plan' }).click();
  await expect(page.getByRole('dialog', { name: 'Unsaved changes' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Discard', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Keep editing' }).click();
  await expect(page.getByLabel('Trip name')).toHaveValue('Aegean summer');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.getByText('Changes saved')).toBeVisible();

  await page.getByLabel('Trip name').fill('Discard this value');
  await page.getByRole('tab', { name: 'Plan' }).click();
  await page.getByRole('button', { name: 'Discard', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Plan' })).toBeVisible();
  await expect(page.getByTestId('trip-preview')).toContainText('Saved guide preview');
  await expect(page.getByTestId('trip-preview')).toContainText('Aegean summer');
  await expect(page.getByTestId('trip-preview')).not.toContainText('Discard this value');
  await page.getByRole('tab', { name: 'Trip details' }).click();
  await expect(page.getByLabel('Trip name')).toHaveValue('Aegean summer');

  await page.getByRole('link', { name: 'Back to My Trips' }).click();
  const updatedTrip = page.getByRole('link', { name: /Aegean summer/ });
  await expect(updatedTrip).toContainText('Athens');
  await expect(updatedTrip).toContainText('2027-06-08 – 2027-06-19');
});

test('editor sees latest values and deliberately reapplies after a revision conflict', async ({ page }) => {
  const trip = editableTrip();
  const latestValues = {
    ...trip,
    revision: 2,
    name: 'Saved elsewhere',
    description: 'Latest saved description',
    destinations: [{
      ...trip.destinations[0],
      timezone: 'Atlantic/Azores',
      location: { lat: 37.74, lng: -25.67 },
    }],
  };
  await page.route('**/api/auth/session', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ account: { id: 'account-one', email: 'editor@example.com', display_name: 'Editor' } }),
  }));
  await page.route('**/api/trips/*/details', async (route) => {
    const request = route.request().postDataJSON();
    if (request.starting_revision === 1) {
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'trip_revision_conflict',
            message: 'This Trip changed after editing started',
            latest_values: latestValues,
          },
        }),
      });
      return;
    }
    expect(request.starting_revision).toBe(2);
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ ...trip, ...request, revision: 3 }),
    });
  });
  await page.route('**/api/trips/*', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify(trip),
  }));

  await page.goto(`/tripper/trips/${trip.id}/edit`);
  await page.getByRole('tab', { name: 'Trip details' }).click();
  await page.getByLabel('Trip name').fill('My retained edit');
  await page.getByRole('button', { name: 'Save changes' }).click();

  await expect(page.getByRole('heading', { name: 'Latest saved values' })).toBeVisible();
  await expect(page.getByText('Saved elsewhere')).toBeVisible();
  await expect(page.getByText('Latest saved description')).toBeVisible();
  await expect(page.getByText(/Atlantic\/Azores/)).toBeVisible();
  await expect(page.getByText(/37.74, -25.67/)).toBeVisible();
  await expect(page.getByLabel('Trip name')).toHaveValue('My retained edit');
  await page.getByRole('button', { name: 'Reapply my changes' }).click();
  await page.getByRole('button', { name: 'Retry save' }).click();
  await expect(page.getByText('Changes saved')).toBeVisible();
});

test('older-revision draft is recovered and compared with latest saved values', async ({ page }) => {
  const trip = { ...editableTrip(), revision: 2, name: 'Saved elsewhere' };
  const recoveredDraft = {
    name: 'Recovered local work',
    short_name: 'Local',
    description: 'Unsaved description',
    start_date: trip.start_date,
    end_date: trip.end_date,
    destinations: [{
      id: trip.destinations[0].id,
      name: 'Local Cyclades',
      timezone: 'Europe/Athens',
      latitude: '',
      longitude: '',
    }],
  };
  await page.addInitScript(({ key, value }) => {
    sessionStorage.setItem(key, value);
  }, {
    key: `tripper:draft:trip_details:account-one:${trip.id}:1`,
    value: JSON.stringify(recoveredDraft),
  });
  await page.route('**/api/auth/session', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ account: { id: 'account-one', email: 'editor@example.com', display_name: 'Editor' } }),
  }));
  await page.route('**/api/trips/*', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify(trip),
  }));

  await page.goto(`/tripper/trips/${trip.id}/edit`);

  await expect(page.getByLabel('Trip name')).toHaveValue('Recovered local work');
  await expect(page.getByText('Unsaved preview')).toBeVisible();
  const conflict = page.locator('.trip-details-form__conflict');
  await expect(conflict.getByRole('heading', { name: 'Latest saved values' })).toBeVisible();
  await expect(conflict).toContainText('Saved elsewhere');
});

test('permission loss keeps values copyable but clears their recoverable draft', async ({ page }) => {
  const trip = editableTrip();
  let permissionLost = false;
  await page.route('**/api/auth/session', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ account: { id: 'account-one', email: 'editor@example.com', display_name: 'Editor' } }),
  }));
  await page.route('**/api/trips/*/details', async (route) => {
    permissionLost = true;
    await route.fulfill({
      status: 403,
      contentType: 'application/json',
      body: JSON.stringify({
        error: { code: 'trip_edit_forbidden', message: 'Trip editing is not permitted' },
      }),
    });
  });
  await page.route('**/api/trips/*', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify(permissionLost ? { ...trip, role: 'traveller' } : trip),
  }));

  await page.goto(`/tripper/trips/${trip.id}/edit`);
  await page.getByRole('tab', { name: 'Trip details' }).click();
  await page.getByLabel('Trip name').fill('Copy this work');
  await page.getByRole('button', { name: 'Save changes' }).click();

  await expect(page.getByRole('alert')).toContainText('available to copy');
  await expect(page.getByLabel('Trip name')).toHaveValue('Copy this work');
  await expect(page.getByLabel('Trip name')).toHaveAttribute('readonly', '');
  await page.reload();
  await expect(page.getByText('Traveller access is read-only.')).toBeVisible();
  await expect(page.getByText('Copy this work')).toHaveCount(0);
});

test('expired Session can be restored without losing active values', async ({ page }) => {
  const trip = editableTrip();
  let saveAttempts = 0;
  await page.addInitScript(() => {
    let googleCallback: (response: { credential: string }) => void;
    window.google = { accounts: { id: {
      initialize(options) { googleCallback = options.callback; },
      renderButton(element) {
        const button = document.createElement('button');
        button.textContent = 'Sign in with Google';
        button.addEventListener('click', () => googleCallback({ credential: 'restored' }));
        element.appendChild(button);
      },
    } } };
  });
  await page.route('**/api/auth/google/config', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ client_id: 'test-client-id' }),
  }));
  await page.route('**/api/auth/google', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ account: { id: 'account-one', email: 'editor@example.com', display_name: 'Editor' } }),
  }));
  await page.route('**/api/auth/session', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ account: { id: 'account-one', email: 'editor@example.com', display_name: 'Editor' } }),
  }));
  await page.route('**/api/trips/*/details', async (route) => {
    saveAttempts += 1;
    if (saveAttempts === 1) {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'authentication_required', message: 'Authentication required' } }),
      });
      return;
    }
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ ...trip, ...route.request().postDataJSON(), revision: 2 }),
    });
  });
  await page.route('**/api/trips/*', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify(trip),
  }));

  await page.goto(`/tripper/trips/${trip.id}/edit`);
  await page.getByRole('tab', { name: 'Trip details' }).click();
  await page.getByLabel('Trip name').fill('Survives sign-in');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.getByLabel('Trip name')).toHaveValue('Survives sign-in');
  await page.getByRole('button', { name: 'Sign in with Google' }).click();
  await expect(page.getByRole('alert')).toContainText('Signed in again');
  await page.getByRole('button', { name: 'Retry save' }).click();
  await expect(page.getByText('Changes saved')).toBeVisible();
});

test('traveller opening an edit URL receives no editing controls', async ({ page }) => {
  await page.route('**/api/auth/session', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        account: {
          id: 'account-one',
          email: 'reader@example.com',
          display_name: 'Reader',
        },
      }),
    });
  });
  await page.route('**/api/trips/read-only', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        id: '223eb014-ff17-51e7-9507-b956164ff7a4',
        revision: 1,
        role: 'traveller',
        name: 'Read-only escape',
        destination: 'Athens',
        short_name: '',
        description: '',
        timezone: 'Europe/Athens',
        location: null,
        start_date: '2027-06-10',
        end_date: '2027-06-10',
        destinations: [{
          id: '7468f63b-f89a-4c08-8cb1-d54fdd2b7389',
          name: 'Athens',
          timezone: 'Europe/Athens',
          location: null,
          position: 0,
          revision: 1,
        }],
        calendar: [{ date: '2027-06-10', day_number: 1, is_planned: false }],
        daily_plans: [],
        roster: [{ display_name: 'Reader', role: 'traveller' }],
      }),
    });
  });

  await page.goto('/tripper/trips/read-only/edit');

  await expect(page.getByRole('heading', { name: 'Read-only escape' })).toBeVisible();
  await expect(page.getByText('Traveller access is read-only.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save changes' })).toHaveCount(0);
  await expect(page.getByRole('tab', { name: 'Trip details' })).toHaveCount(0);
});
