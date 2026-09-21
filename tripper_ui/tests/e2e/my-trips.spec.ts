import { expect, test } from '@playwright/test';

test('user creates a trip and finds it in My Trips as creator', async ({ page }) => {
  await page.goto('/tripper/my-trips');

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

  const trip = page.getByRole('link', { name: /Greek Islands 2027/ });
  await expect(trip).toContainText('Cyclades');
  await expect(trip).toContainText('Creator');

  await page.reload();
  await expect(page.getByRole('link', { name: /Greek Islands 2027/ })).toContainText('Creator');

  const persistedTrip = page.getByRole('link', { name: /Greek Islands 2027/ });
  await persistedTrip.click();
  await expect(page.getByRole('heading', { name: 'Greek Islands 2027' })).toBeVisible();
  await expect(page.getByText('No days planned yet.')).toBeVisible();
});
