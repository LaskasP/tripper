import './MapButton.css';
import { googleMapsUrl } from '../../lib/maps';
import type { Location } from '../../types';

export function createMapButton(location: Location | string, label = 'Open in Maps'): HTMLAnchorElement {
  const el = document.createElement('a');
  el.className = 'map-button';
  el.href = typeof location === 'string' ? googleMapsUrl(location) : googleMapsUrl(location);
  el.target = '_blank';
  el.rel = 'noopener noreferrer';

  const icon = document.createElement('span');
  icon.className = 'map-button__icon';
  icon.textContent = '📍';

  const text = document.createElement('span');
  text.className = 'map-button__label';
  text.textContent = label;

  el.appendChild(icon);
  el.appendChild(text);
  return el;
}
