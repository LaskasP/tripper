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
  await expect(page.getByText('Saved guide preview')).toBeVisible();
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

test('editor manages independent Timeline entries and readers get no editing controls', async ({ page }) => {
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
  await page.getByLabel('Trip name').fill('Timeline editing');
  await page.getByLabel('Destination').fill('Athens');
  await page.getByLabel('Timezone').fill('Europe/Athens');
  await page.getByLabel('Start date').fill('2027-06-10');
  await page.getByLabel('End date').fill('2027-06-11');
  await page.getByRole('button', { name: 'Save trip' }).click();
  await expect(page).toHaveURL(/\/edit$/);
  const tripUrl = page.url().replace(/\/edit$/, '');

  await page.getByLabel('Day title').fill('Arrival');
  await page.getByRole('button', { name: 'Save plan' }).click();
  await expect(page.getByRole('button', { name: 'Add activity' })).toBeVisible();
  await page.getByRole('button', { name: 'June 11, 2027' }).click();
  await page.getByLabel('Day title').fill('Second day');
  await page.getByRole('button', { name: 'Save plan' }).click();
  await expect(page.getByRole('button', { name: 'Add activity' })).toBeVisible();
  await page.getByRole('button', { name: 'June 10, 2027' }).click();

  await page.getByRole('button', { name: 'Add activity' }).click();
  await page.getByLabel('Activity time').fill('10:00');
  await page.getByLabel('Activity title').fill('Museum');
  await page.reload();
  await expect(page.getByLabel('Activity title')).toHaveValue('Museum');
  await expect(page.getByText('Unsaved preview')).toBeVisible();
  await page.getByRole('button', { name: 'Save activity' }).click();
  await expect(page.getByRole('button', { name: 'Edit Museum' })).toBeVisible();
  await page.getByRole('button', { name: 'Add activity' }).click();
  await page.getByLabel('Activity time').fill('10:00');
  await page.getByLabel('Activity title').fill('Coffee');
  await page.getByRole('button', { name: 'Save activity' }).click();
  await expect(page.getByRole('button', { name: 'Edit Coffee' })).toBeVisible();
  await page.getByRole('button', { name: 'Move Coffee up' }).click();
  await expect(page.locator('.timeline-editor__item').nth(0)).toContainText('Coffee');
  await page.getByRole('button', { name: 'Edit Museum' }).click();
  await page.getByLabel('Activity title').fill('Museum tour');
  await page.evaluate(async (id) => {
    const detail = await (await fetch(`/api/trips/${id}`)).json();
    const plan = detail.daily_plans.find((item: { date: string }) => item.date === '2027-06-10');
    const entry = plan.timeline.find((item: { title: string }) => item.title === 'Museum');
    const csrf = document.cookie.split('; ').find((item) => item.startsWith('tripper_csrf='))?.split('=')[1];
    await fetch(`/api/trips/${id}/daily-plans/${plan.id}/timeline/${entry.id}`, {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': decodeURIComponent(csrf || '') },
      body: JSON.stringify({
        starting_revision: entry.revision, destination_id: entry.destination_id,
        time: entry.time, title: 'Changed elsewhere', description: '', location_name: null,
      }),
    });
  }, tripUrl.split('/').at(-1));
  await page.getByRole('button', { name: 'Save activity' }).click();
  await expect(page.getByText('Latest saved activity')).toBeVisible();
  await expect(page.getByText('Changed elsewhere').first()).toBeVisible();
  await expect(page.getByLabel('Activity title')).toHaveValue('Museum tour');
  await page.getByRole('button', { name: 'Reapply my activity' }).click();
  await page.getByRole('button', { name: 'Save activity' }).click();
  await expect(page.getByRole('button', { name: 'Edit Museum tour' })).toBeVisible();
  await page.getByLabel('Move Museum tour to date').selectOption('2027-06-11');
  await page.getByRole('button', { name: 'Move Museum tour', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Edit Museum tour' })).toHaveCount(0);

  const reader = await page.context().newPage();
  await reader.goto(tripUrl);
  await expect(reader.getByText('Coffee')).toBeVisible();
  await expect(reader.getByText('Museum tour')).toBeVisible();
  await expect(reader.getByRole('button', { name: 'Add activity' })).toHaveCount(0);
  await expect(reader.getByRole('button', { name: /Edit Museum tour/ })).toHaveCount(0);
  await reader.close();
});

test('editor manages a public-safe Stay and the guide remains read-only', async ({ page }) => {
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
  await page.getByLabel('Trip name').fill('Stay editing');
  await page.getByLabel('Destination').fill('Naxos');
  await page.getByLabel('Timezone').fill('Europe/Athens');
  await page.getByLabel('Start date').fill('2027-06-10');
  await page.getByLabel('End date').fill('2027-06-10');
  await page.getByRole('button', { name: 'Save trip' }).click();
  await page.getByLabel('Day title').fill('Island arrival');
  await page.getByRole('button', { name: 'Save plan' }).click();

  await page.getByRole('button', { name: 'Add stay' }).click();
  await page.getByLabel('Accommodation name').fill('Aegean House');
  await page.getByLabel('Address').fill('Port Road 1');
  await page.getByLabel('Latitude').fill('37.45');
  await page.getByLabel('Longitude').fill('25.33');
  await page.getByLabel('Check-in time').fill('15:00');
  await page.getByLabel('Check-out time').fill('11:00');
  await page.getByLabel('Booking platform').selectOption('airbnb');
  await page.getByLabel('Public listing HTTPS URL').fill('https://example.com/aegean-house');
  await page.getByRole('button', { name: 'Save stay' }).click();
  await expect(page.getByText('Aegean House · Port Road 1')).toBeVisible();

  const guide = await page.context().newPage();
  await guide.goto(page.url().replace(/\/edit$/, ''));
  await expect(guide.getByRole('heading', { name: 'Aegean House' })).toBeVisible();
  await expect(guide.getByText('Port Road 1')).toBeVisible();
  await expect(guide.getByRole('link', { name: 'Airbnb' })).toHaveAttribute(
    'href',
    'https://example.com/aegean-house',
  );
  await expect(guide.getByRole('button', { name: 'Edit stay' })).toHaveCount(0);

  await page.getByRole('button', { name: 'Edit stay' }).click();
  await page.getByLabel('Accommodation name').fill('Aegean Suites');
  await page.getByRole('button', { name: 'Save stay' }).click();
  await expect(page.getByText('Aegean Suites · Port Road 1')).toBeVisible();
  await page.getByRole('button', { name: 'Clear stay' }).click();
  await expect(page.getByRole('button', { name: 'Add stay' })).toBeVisible();
  await guide.reload();
  await expect(guide.getByText('Aegean House')).toHaveCount(0);
  await guide.close();
});

test('editor adds, recovers, reorders, and removes Daily plan photos', async ({ page }) => {
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
  await page.getByLabel('Trip name').fill('Photo editing');
  await page.getByLabel('Destination').fill('Athens');
  await page.getByLabel('Timezone').fill('Europe/Athens');
  await page.getByLabel('Start date').fill('2027-06-10');
  await page.getByLabel('End date').fill('2027-06-10');
  await page.getByRole('button', { name: 'Save trip' }).click();
  await expect(page).toHaveURL(/\/edit$/);
  const tripUrl = page.url().replace(/\/edit$/, '');
  await page.getByLabel('Day title').fill('Photo day');
  await page.getByRole('button', { name: 'Save plan' }).click();

  await page.getByRole('button', { name: 'Add photo' }).click();
  await page.getByLabel('Photo HTTPS URL').fill('https://images.example/harbour.jpg');
  await page.getByLabel('Photo caption').fill('Harbour at sunset');
  await page.evaluate(async (id) => {
    const detail = await (await fetch(`/api/trips/${id}`)).json();
    const plan = detail.daily_plans[0];
    const csrf = document.cookie.split('; ').find((item) => item.startsWith('tripper_csrf='))?.split('=')[1];
    await fetch(`/api/trips/${id}/daily-plans/${plan.id}/photos`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': decodeURIComponent(csrf || '') },
      body: JSON.stringify({
        starting_revision: plan.photo_revision,
        url: 'https://images.example/elsewhere.jpg',
        caption: 'Changed elsewhere',
      }),
    });
  }, tripUrl.split('/').at(-1));
  await page.reload();
  await expect(page.getByLabel('Photo HTTPS URL')).toHaveValue('https://images.example/harbour.jpg');
  await expect(page.getByText('Unsaved preview')).toBeVisible();
  await expect(page.getByText('Latest saved photos')).toBeVisible();
  await expect(page.getByText('Changed elsewhere').first()).toBeVisible();
  await page.getByRole('button', { name: 'Reapply my photo' }).click();
  await page.getByRole('button', { name: 'Save photo' }).click();

  await page.getByRole('button', { name: 'Add photo' }).click();
  await page.getByLabel('Photo HTTPS URL').fill('http://images.example/insecure.jpg');
  await page.getByRole('button', { name: 'Save photo' }).click();
  await expect(page.getByRole('alert')).toContainText('Enter an HTTPS photo URL');
  await page.getByLabel('Photo HTTPS URL').fill('https://images.example/acropolis.jpg');
  await page.getByLabel('Photo caption').fill('Acropolis morning');
  await page.getByRole('button', { name: 'Save photo' }).click();
  await page.getByRole('button', { name: 'Move Acropolis morning up' }).click();
  await expect(page.locator('.photo-editor__item').nth(1)).toContainText('Acropolis morning');
  await page.getByRole('button', { name: 'Remove Harbour at sunset' }).click();

  const reader = await page.context().newPage();
  await reader.goto(tripUrl);
  await expect(reader.getByRole('img', { name: 'Acropolis morning' })).toBeVisible();
  await expect(reader.getByRole('img', { name: 'Harbour at sunset' })).toHaveCount(0);
  await expect(reader.getByRole('button', { name: 'Add photo' })).toHaveCount(0);
  await reader.close();
});
