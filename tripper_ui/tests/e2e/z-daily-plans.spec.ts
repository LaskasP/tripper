import { expect, test } from '@playwright/test';

test('editor saves, moves, and clears a Daily plan while the guide stays read-only', async ({ page }) => {
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
  await page.getByLabel('Trip name').fill('Daily plan editing');
  await page.getByLabel('Destination').fill('Athens');
  await page.getByLabel('Timezone').fill('Europe/Athens');
  await page.getByLabel('Start date').fill('2027-06-10');
  await page.getByLabel('End date').fill('2027-06-12');
  await page.getByRole('button', { name: 'Save trip' }).click();
  await expect(page).toHaveURL(/\/edit$/);
  const tripUrl = page.url().replace(/\/edit$/, '');

  await page.getByLabel('Day title').fill('Ferry day');
  await page.getByLabel('Day summary').fill('Take the ferry');
  await page.reload();
  await expect(page.getByLabel('Day title')).toHaveValue('Ferry day');
  await expect(page.getByLabel('Day summary')).toHaveValue('Take the ferry');
  await expect(page.getByText('Unsaved preview')).toBeVisible();
  const reader = await page.context().newPage();
  await reader.goto(tripUrl);
  await expect(reader.getByText('Not planned yet').first()).toBeVisible();
  await expect(reader.getByText('Ferry day')).toHaveCount(0);
  await page.getByRole('button', { name: 'Save plan' }).click();
  await reader.reload();
  await expect(reader.getByRole('heading', { name: 'Ferry day' })).toBeVisible();
  await expect(reader.getByText('Take the ferry')).toBeVisible();

  await page.getByLabel('Day summary').fill('My revised ferry notes');
  await page.evaluate(async (id) => {
    const detail = await (await fetch(`/api/trips/${id}`)).json();
    const plan = detail.daily_plans[0];
    const csrf = document.cookie.split('; ').find((item) => item.startsWith('tripper_csrf='))?.split('=')[1];
    await fetch(`/api/trips/${id}/daily-plans/${plan.date}`, {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': decodeURIComponent(csrf || '') },
      body: JSON.stringify({
        id: plan.id, starting_revision: plan.revision, destination_id: plan.destination_id,
        title: 'Changed elsewhere', summary: 'Server summary', background_image: '',
      }),
    });
  }, tripUrl.split('/').at(-1));
  await page.reload();
  await expect(page.getByLabel('Day summary')).toHaveValue('My revised ferry notes');
  const conflict = page.locator('.trip-details-form__conflict');
  await expect(conflict).toContainText('Changed elsewhere');
  await expect(conflict).toContainText('Server summary');
  await conflict.getByRole('button', { name: 'Reapply my changes' }).click();
  await page.getByRole('button', { name: 'Save plan' }).click();
  await reader.reload();
  await expect(reader.getByText('My revised ferry notes')).toBeVisible();

  await page.evaluate(async (id) => {
    const detail = await (await fetch(`/api/trips/${id}`)).json();
    const plan = detail.daily_plans[0];
    const csrf = document.cookie.split('; ').find((item) => item.startsWith('tripper_csrf='))?.split('=')[1];
    await fetch(`/api/trips/${id}/daily-plans/${plan.date}`, {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': decodeURIComponent(csrf || '') },
      body: JSON.stringify({
        id: plan.id, starting_revision: plan.revision, destination_id: plan.destination_id,
        title: plan.title, summary: 'Newer move notes', background_image: '',
      }),
    });
  }, tripUrl.split('/').at(-1));
  await page.getByLabel('Move complete plan to').selectOption('2027-06-11');
  await page.getByRole('button', { name: 'Move plan' }).click();
  await expect(page.locator('.trip-details-form__conflict')).toContainText('Newer move notes');
  await page.getByRole('button', { name: 'Retry move' }).click();
  await expect(page.getByLabel('Day title')).toHaveValue('Ferry day');
  await reader.reload();
  await expect(reader.getByRole('heading', { name: 'Ferry day' })).toBeVisible();
  page.on('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Clear plan' }).click();
  await reader.reload();
  await expect(reader.getByRole('heading', { name: 'Ferry day' })).toHaveCount(0);
  await expect(reader.getByText('Not planned yet').first()).toBeVisible();
  await reader.close();
});
