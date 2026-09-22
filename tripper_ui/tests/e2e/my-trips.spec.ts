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

  await page.goto('/tripper/my-trips');
  const trip = page.getByRole('link', { name: /Greek Islands 2027/ });
  await expect(trip).toContainText('Cyclades');
  await expect(trip).toContainText('Creator');

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
