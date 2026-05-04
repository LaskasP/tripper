import './AppHeader.css';

export function createAppHeader(tripName: string): HTMLElement {
  const el = document.createElement('header');
  el.className = 'app-header';
  el.setAttribute('aria-live', 'polite');

  const trip = document.createElement('span');
  trip.className = 'app-header__trip';
  trip.textContent = tripName;

  const dayInfo = document.createElement('span');
  dayInfo.className = 'app-header__day';
  dayInfo.dataset.dayInfo = '';

  el.appendChild(trip);
  el.appendChild(dayInfo);
  return el;
}

export function updateAppHeader(header: HTMLElement, dayNumber: number, date: string): void {
  const dayInfo = header.querySelector<HTMLElement>('[data-day-info]');
  if (!dayInfo) return;
  const d = new Date(date + 'T00:00:00');
  const formatted = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  dayInfo.textContent = `Day ${dayNumber} · ${formatted}`;
}
