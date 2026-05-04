import './Timeline.css';
import { createTimelineItem } from '../TimelineItem';
import type { TimelineEntry } from '../../types';

export function createTimeline(entries: TimelineEntry[]): HTMLElement {
  const el = document.createElement('section');
  el.className = 'timeline';

  const heading = document.createElement('h3');
  heading.className = 'timeline__heading';
  heading.textContent = 'Schedule';

  const list = document.createElement('ul');
  list.className = 'timeline__list';

  for (const entry of entries) {
    list.appendChild(createTimelineItem(entry));
  }

  el.appendChild(heading);
  el.appendChild(list);
  return el;
}
