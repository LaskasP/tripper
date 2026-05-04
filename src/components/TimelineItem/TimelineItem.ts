import './TimelineItem.css';
import { createMapButton } from '../MapButton';
import type { TimelineEntry } from '../../types';

export function createTimelineItem(entry: TimelineEntry): HTMLElement {
  const el = document.createElement('li');
  el.className = 'timeline-item';

  const pill = document.createElement('span');
  pill.className = 'timeline-item__time';
  pill.textContent = entry.time;

  const body = document.createElement('div');
  body.className = 'timeline-item__body';

  const title = document.createElement('h4');
  title.className = 'timeline-item__title';
  title.textContent = entry.title;

  const desc = document.createElement('p');
  desc.className = 'timeline-item__desc';
  desc.textContent = entry.description;

  body.appendChild(title);
  body.appendChild(desc);

  if (entry.location) {
    const mapBtn = createMapButton(
      entry.location,
      entry.locationName ?? 'View on Map',
    );
    body.appendChild(mapBtn);
  }

  el.appendChild(pill);
  el.appendChild(body);
  return el;
}
