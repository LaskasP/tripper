/**
 * PROTOTYPE — throw away after the editing-surface decision is captured.
 * Three hybrid editor variants, switchable via ?variant=A|B|C, on a standalone
 * page because Tripper does not yet have an editing route.
 */
import './editing-workspace-prototype.css';

type Variant = 'A' | 'B' | 'C';

interface PrototypeState {
  tripName: string;
  selectedDay: number;
  dayTitle: string;
  summary: string;
  activities: Array<{ time: string; title: string }>;
  stay: string;
  saved: boolean;
}

const variants: Array<{ key: Variant; name: string }> = [
  { key: 'A', name: 'Preview + sheet' },
  { key: 'B', name: 'Planner workspace' },
  { key: 'C', name: 'Inline canvas' },
];

const state: PrototypeState = {
  tripName: 'Los Angeles 2026',
  selectedDay: 2,
  dayTitle: 'Downtown LA Highlights',
  summary: 'A full day exploring The Broad, Grand Central Market, Union Station, and Little Tokyo.',
  activities: [
    { time: '09:30', title: 'The Broad' },
    { time: '11:30', title: 'Grand Central Market' },
    { time: '13:00', title: 'Union Station & Olvera Street' },
  ],
  stay: 'Fashion Loft',
  saved: true,
};

const prototypeRoot = document.querySelector<HTMLElement>('#prototype-app');
if (!prototypeRoot) throw new Error('Prototype root not found');
const app: HTMLElement = prototypeRoot;

function currentVariant(): Variant {
  const requested = new URLSearchParams(window.location.search).get('variant')?.toUpperCase();
  return requested === 'B' || requested === 'C' ? requested : 'A';
}

function setVariant(variant: Variant): void {
  const url = new URL(window.location.href);
  url.searchParams.set('variant', variant);
  window.history.replaceState({}, '', url);
  render();
}

function cycleVariant(direction: number): void {
  const index = variants.findIndex(({ key }) => key === currentVariant());
  const next = (index + direction + variants.length) % variants.length;
  setVariant(variants[next].key);
}

function guidePreview(extraClass = ''): string {
  return `
    <article class="guide-preview ${extraClass}" aria-label="Day 2 guide preview">
      <div class="guide-preview__shade"></div>
      <header class="guide-header">
        <div><strong>${state.tripName}</strong><span>Day 2 · Sat, Nov 14</span></div>
        <button class="icon-button account-button" type="button" aria-label="Open account menu">PL</button>
      </header>
      <div class="guide-preview__content">
        <p class="eyebrow">Day 2</p>
        <h1>${state.dayTitle}</h1>
        <div class="weather">☀ 22°</div>
        <p class="summary">${state.summary}</p>
        <section class="glass-card schedule">
          <div class="section-heading"><h2>Schedule</h2><span>${state.activities.length} stops</span></div>
          ${state.activities.map((activity) => `
            <div class="timeline-row"><time>${activity.time}</time><strong>${activity.title}</strong><span>↗ Map</span></div>
          `).join('')}
        </section>
        <section class="glass-card stay"><span class="stay__icon">⌂</span><div><small>Stay</small><strong>${state.stay}</strong></div><span>↗ Map</span></section>
        <section class="photos" aria-label="Photos">
          <div><span>The Broad museum</span></div><div><span>Grand Central Market</span></div>
        </section>
      </div>
      <div class="dot-nav" aria-hidden="true"><i></i><i class="active"></i><i></i><i></i><i></i></div>
    </article>`;
}

function dayForm(compact = false): string {
  return `
    <form class="day-form ${compact ? 'day-form--compact' : ''}" data-day-form>
      <div class="form-heading"><div><p class="eyebrow">Day 2 · Nov 14</p><h2>Edit day</h2></div><span class="save-state">${state.saved ? 'Saved' : 'Unsaved'}</span></div>
      <label>Day title<input name="dayTitle" value="${state.dayTitle}" /></label>
      <label>Summary<textarea name="summary" rows="3">${state.summary}</textarea></label>
      <fieldset><legend>Schedule</legend>
        ${state.activities.map((activity, index) => `
          <div class="activity-field"><button type="button" aria-label="Move ${activity.title}">↕</button><input aria-label="Time" name="time-${index}" value="${activity.time}" /><input aria-label="Activity title" name="activity-${index}" value="${activity.title}" /><button type="button" aria-label="More options">•••</button></div>
        `).join('')}
        <button class="secondary-button full-button" type="button">＋ Add activity</button>
      </fieldset>
      <label>Stay<input name="stay" value="${state.stay}" /></label>
      <div class="form-actions"><button class="secondary-button" type="button" data-cancel>Cancel</button><button class="primary-button" type="submit">Save day</button></div>
    </form>`;
}

function variantA(): string {
  return `
    <main class="variant variant-a">
      <div class="prototype-note"><strong>A · Preview + sheet</strong><span>Browse the real guide; edit one focused section in a sheet.</span></div>
      ${guidePreview()}
      <button class="edit-fab" type="button" data-toggle-sheet>✎ Edit this day</button>
      <aside class="editor-sheet is-open" aria-label="Day editor">
        <button class="sheet-handle" type="button" data-toggle-sheet aria-label="Toggle editor"></button>
        ${dayForm(true)}
      </aside>
    </main>`;
}

function variantB(): string {
  const dayNames = ['Arrival at Downtown LA', state.dayTitle, 'Last Day in LA', 'LA to Las Vegas', 'Las Vegas Day'];
  return `
    <main class="variant variant-b">
      <header class="workspace-header"><a href="#">← My Trips</a><div><strong>${state.tripName}</strong><span class="save-state">${state.saved ? 'All changes saved' : 'Unsaved changes'}</span></div><button class="icon-button account-button" type="button">PL</button></header>
      <div class="workspace-tabs"><button class="active">Guide</button><button>People</button><button>Publish</button><button>Trip settings</button></div>
      <div class="planner-layout">
        <nav class="day-list" aria-label="Trip days">
          <div class="day-list__heading"><strong>14 days</strong><button type="button">＋</button></div>
          ${dayNames.map((name, index) => `<button class="${index === 1 ? 'active' : ''}" type="button"><span>${index + 1}</span><div><small>Nov ${13 + index}</small><strong>${name}</strong></div></button>`).join('')}
        </nav>
        <section class="planner-form">${dayForm()}</section>
        <aside class="desktop-preview">${guidePreview('guide-preview--phone')}</aside>
      </div>
      <button class="mobile-preview-button" type="button" data-toggle-preview>◉ Preview</button>
    </main>`;
}

function variantC(): string {
  return `
    <main class="variant variant-c">
      <div class="canvas-toolbar"><button type="button">← Done</button><div><strong>Editing Day 2</strong><span class="save-state">${state.saved ? 'Saved' : 'Unsaved'}</span></div><button class="primary-button" type="button" data-save>Save</button></div>
      ${guidePreview('guide-preview--canvas')}
      <button class="inline-edit inline-edit--title" type="button" data-inspect="title">✎ Title</button>
      <button class="inline-edit inline-edit--summary" type="button" data-inspect="summary">✎ Summary</button>
      <button class="inline-edit inline-edit--schedule" type="button" data-inspect="schedule">✎ Schedule</button>
      <aside class="inspector is-open" aria-label="Contextual editor">
        <div class="inspector__heading"><div><p class="eyebrow">Selected section</p><h2>Schedule</h2></div><button type="button" data-close-inspector>×</button></div>
        <p class="muted">Select a highlighted part of the guide to edit it here.</p>
        ${dayForm(true)}
      </aside>
    </main>`;
}

function switcher(): string {
  if (import.meta.env.PROD) return '';
  const variant = variants.find(({ key }) => key === currentVariant())!;
  return `<nav class="prototype-switcher" aria-label="Prototype variants"><button type="button" data-previous aria-label="Previous variant">←</button><span>${variant.key} — ${variant.name}</span><button type="button" data-next aria-label="Next variant">→</button></nav>`;
}

function statePanel(): string {
  return `<details class="state-panel"><summary>Prototype state</summary><pre>${JSON.stringify(state, null, 2)}</pre></details>`;
}

function render(): void {
  const variant = currentVariant();
  document.body.dataset.variant = variant;
  app.innerHTML = `${variant === 'A' ? variantA() : variant === 'B' ? variantB() : variantC()}${statePanel()}${switcher()}`;
  bindInteractions();
}

function bindInteractions(): void {
  app.querySelector('[data-previous]')?.addEventListener('click', () => cycleVariant(-1));
  app.querySelector('[data-next]')?.addEventListener('click', () => cycleVariant(1));
  app.querySelectorAll('[data-toggle-sheet]').forEach((button) => button.addEventListener('click', () => app.querySelector('.editor-sheet')?.classList.toggle('is-open')));
  app.querySelector('[data-toggle-preview]')?.addEventListener('click', () => app.querySelector('.desktop-preview')?.classList.toggle('is-mobile-open'));
  app.querySelector('[data-close-inspector]')?.addEventListener('click', () => app.querySelector('.inspector')?.classList.remove('is-open'));
  app.querySelectorAll('[data-inspect]').forEach((button) => button.addEventListener('click', () => app.querySelector('.inspector')?.classList.add('is-open')));
  app.querySelector('[data-save]')?.addEventListener('click', () => { state.saved = true; render(); });

  app.querySelectorAll<HTMLFormElement>('[data-day-form]').forEach((form) => {
    form.addEventListener('input', () => {
      state.saved = false;
      app.querySelectorAll('.save-state').forEach((node) => { node.textContent = 'Unsaved'; });
    });
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const data = new FormData(form);
      state.dayTitle = String(data.get('dayTitle') ?? state.dayTitle);
      state.summary = String(data.get('summary') ?? state.summary);
      state.stay = String(data.get('stay') ?? state.stay);
      state.activities = state.activities.map((activity, index) => ({
        time: String(data.get(`time-${index}`) ?? activity.time),
        title: String(data.get(`activity-${index}`) ?? activity.title),
      }));
      state.saved = true;
      render();
    });
    form.querySelector('[data-cancel]')?.addEventListener('click', () => render());
  });
}

window.addEventListener('keydown', (event) => {
  const target = event.target as HTMLElement;
  if (target.matches('input, textarea, [contenteditable]')) return;
  if (event.key === 'ArrowLeft') cycleVariant(-1);
  if (event.key === 'ArrowRight') cycleVariant(1);
});

window.addEventListener('popstate', render);
render();
