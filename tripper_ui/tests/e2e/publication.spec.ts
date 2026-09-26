import { expect, test } from '@playwright/test';

test('Creator publishes, rotates, and unpublishes an anonymous guide', async ({ browser, page }) => {
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
  await page.getByLabel('Trip name').fill('Published Athens');
  await page.getByLabel('Destination').fill('Athens');
  await page.getByLabel('Timezone').fill('Europe/Athens');
  await page.getByLabel('Start date').fill('2027-06-10');
  await page.getByLabel('End date').fill('2027-06-10');
  await page.getByRole('button', { name: 'Save trip' }).click();
  await page.getByLabel('Day title').fill('Acropolis day');
  await page.getByRole('button', { name: 'Save plan' }).click();
  await expect(page.getByText('Saved guide preview')).toBeVisible();

  await page.getByRole('tab', { name: 'Publish' }).click();
  await expect(page.getByText('This Trip is a private Draft.')).toBeVisible();
  await expect(page.getByText(/Anyone with the unlisted link/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Preview saved guide' })).toHaveAttribute(
    'href',
    /\/tripper\/trips\//,
  );
  await page.getByRole('button', { name: 'Publish guide' }).click();
  const publicLink = page.locator('.publication-panel__link');
  await expect(publicLink).toBeVisible();
  const firstUrl = await publicLink.getAttribute('href');
  expect(firstUrl).toBeTruthy();

  const anonymous = await browser.newPage();
  await anonymous.goto(firstUrl!);
  await expect(anonymous.locator('meta[name="robots"]')).toHaveAttribute(
    'content',
    'noindex, nofollow',
  );
  await expect(anonymous.getByRole('heading', { name: 'Acropolis day' })).toBeVisible();

  page.on('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Rotate link' }).click();
  await expect(publicLink).not.toHaveAttribute('href', firstUrl!);
  await anonymous.reload();
  await expect(anonymous.getByText('Trip not found')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Rotate link' })).toBeVisible();

  const secondUrl = await publicLink.getAttribute('href');
  await anonymous.goto(secondUrl!);
  await expect(anonymous.getByRole('heading', { name: 'Acropolis day' })).toBeVisible();
  await page.getByRole('button', { name: 'Unpublish' }).click();
  await anonymous.reload();
  await expect(anonymous.getByText('Trip not found')).toBeVisible();
  await anonymous.close();
});
