import './Day.css';
import { createDayHeader } from '../DayHeader';
import { createTimeline } from '../Timeline';
import { createStayCard } from '../StayCard';
import { createPhotoStrip } from '../PhotoStrip';
import type { Day } from '../../types';

export function createDay(day: Day): HTMLElement {
  const section = document.createElement('section');
  section.className = 'day';
  section.id = `day-${day.dayNumber}`;
  section.style.backgroundImage = `url('${day.backgroundImage.replace(/'/g, "\\'")}')`;

  const overlay = document.createElement('div');
  overlay.className = 'day__overlay';

  const scroll = document.createElement('div');
  scroll.className = 'day__scroll';

  scroll.appendChild(createDayHeader(day.dayNumber, day.date, day.title, day.weather));

  const summary = document.createElement('p');
  summary.className = 'day__summary';
  summary.textContent = day.summary;
  scroll.appendChild(summary);

  scroll.appendChild(createTimeline(day.timeline));

  scroll.appendChild(createStayCard(day.stay));

  if (day.photos.length > 0) {
    scroll.appendChild(createPhotoStrip(day.photos));
  }

  // spacer at bottom for comfortable scroll
  const spacer = document.createElement('div');
  spacer.className = 'day__spacer';
  scroll.appendChild(spacer);

  overlay.appendChild(scroll);
  section.appendChild(overlay);
  return section;
}
