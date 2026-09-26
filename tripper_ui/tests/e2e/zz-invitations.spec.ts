import { expect, test } from '@playwright/test';

test('Creator sends, replaces, and revokes a pending invitation', async ({ page }) => {
  await page.addInitScript(() => {
    let googleCallback: (response: { credential: string }) => void;
    window.google = { accounts: { id: {
      initialize(options) { googleCallback = options.callback; },
      renderButton(element) {
        const button = document.createElement('button');
        button.textContent = 'Sign in with Google';
        button.addEventListener('click', () => googleCallback({ credential: 'e2e-google-credential' }));
        element.appendChild(button);
      },
    } } };
  });

  await page.goto('/tripper/my-trips');
  await page.getByRole('button', { name: 'Sign in with Google' }).click();
  await page.getByRole('button', { name: 'Create trip' }).click();
  await page.getByLabel('Trip name').fill('Invitation Trip');
  await page.getByLabel('Destination').fill('Athens');
  await page.getByLabel('Timezone').fill('Europe/Athens');
  await page.getByLabel('Start date').fill('2027-06-10');
  await page.getByLabel('End date').fill('2027-06-11');
  await page.getByRole('button', { name: 'Save trip' }).click();
  await page.getByRole('tab', { name: 'People' }).click();

  await expect(page.getByText('No pending invitations.')).toBeVisible();
  await page.getByLabel('Email').fill('friend@example.com');
  await page.getByLabel('Trip role').selectOption('traveller');
  await page.getByRole('button', { name: 'Send invitation' }).click();
  await expect(page.getByText('friend@example.com · Traveller · Queued')).toBeVisible();

  page.on('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Replace' }).click();
  await expect(page.getByText('Replacement queued for friend@example.com.')).toBeVisible();
  await page.getByRole('button', { name: 'Revoke' }).click();
  await expect(page.getByText('Invitation for friend@example.com revoked.')).toBeVisible();
  await expect(page.getByText('friend@example.com · Traveller · Queued')).toHaveCount(0);
});
