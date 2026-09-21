import './DayHeader.css';
import type { Weather } from '../../types';

export function createDayHeader(
  dayNumber: number,
  date: string,
  title: string,
  weather?: Weather,
): HTMLElement {
  const el = document.createElement('header');
  el.className = 'day-header';

  const dateEl = document.createElement('div');
  dateEl.className = 'day-header__date';
  const d = new Date(date + 'T00:00:00');
  dateEl.textContent = d.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  const dayNum = document.createElement('span');
  dayNum.className = 'day-header__number';
  dayNum.textContent = `Day ${dayNumber}`;

  const titleEl = document.createElement('h2');
  titleEl.className = 'day-header__title';
  titleEl.textContent = title;

  el.appendChild(dayNum);
  el.appendChild(dateEl);
  el.appendChild(titleEl);

  if (weather) {
    const weatherEl = document.createElement('div');
    weatherEl.className = 'day-header__weather';

    const wIcon = document.createElement('span');
    wIcon.className = 'day-header__weather-icon';
    wIcon.textContent = weather.icon;

    const wText = document.createElement('span');
    wText.className = 'day-header__weather-text';
    wText.textContent = `${weather.high}°C / ${weather.low}°C · ${weather.description}`;

    weatherEl.appendChild(wIcon);
    weatherEl.appendChild(wText);
    el.appendChild(weatherEl);
  }

  return el;
}
