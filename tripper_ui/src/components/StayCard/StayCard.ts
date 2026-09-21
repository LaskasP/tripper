import './StayCard.css';
import { createMapButton } from '../MapButton';
import type { Stay } from '../../types';

export function createStayCard(stay: Stay): HTMLElement {
  const el = document.createElement('section');
  el.className = 'stay-card';

  const icon = document.createElement('span');
  icon.className = 'stay-card__icon';
  icon.textContent = '🏨';

  const info = document.createElement('div');
  info.className = 'stay-card__info';

  const name = document.createElement('h4');
  name.className = 'stay-card__name';
  name.textContent = stay.name;

  const address = document.createElement('p');
  address.className = 'stay-card__address';
  address.textContent = stay.address;

  info.appendChild(name);
  info.appendChild(address);

  if (stay.checkIn) {
    const ci = document.createElement('span');
    ci.className = 'stay-card__badge';
    ci.textContent = `Check-in ${stay.checkIn}`;
    info.appendChild(ci);
  }
  if (stay.checkOut) {
    const co = document.createElement('span');
    co.className = 'stay-card__badge';
    co.textContent = `Check-out ${stay.checkOut}`;
    info.appendChild(co);
  }

  const actions = document.createElement('div');
  actions.className = 'stay-card__actions';

  actions.appendChild(createMapButton(stay.location, stay.name));

  if (stay.bookingUrl) {
    const bookingLink = document.createElement('a');
    bookingLink.className = 'stay-card__booking';
    bookingLink.href = stay.bookingUrl;
    bookingLink.target = '_blank';
    bookingLink.rel = 'noopener noreferrer';

    const platformIcon = document.createElement('span');
    platformIcon.className = 'stay-card__booking-icon';
    platformIcon.textContent = stay.platform === 'airbnb' ? '🏠' : '🔖';

    const platformText = document.createElement('span');
    platformText.textContent = stay.platform === 'airbnb' ? 'Airbnb' : 'Booking.com';

    bookingLink.appendChild(platformIcon);
    bookingLink.appendChild(platformText);
    actions.appendChild(bookingLink);
  }

  el.appendChild(icon);
  el.appendChild(info);
  el.appendChild(actions);
  return el;
}
