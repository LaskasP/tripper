import './PhotoStrip.css';
import type { PhotoItem } from '../../types';

export function createPhotoStrip(photos: PhotoItem[]): HTMLElement {
  const el = document.createElement('section');
  el.className = 'photo-strip';

  const heading = document.createElement('h3');
  heading.className = 'photo-strip__heading';
  heading.textContent = 'Photos';

  const track = document.createElement('div');
  track.className = 'photo-strip__track';

  for (const photo of photos) {
    const card = document.createElement('figure');
    card.className = 'photo-strip__card';

    const img = document.createElement('img');
    img.className = 'photo-strip__img';
    img.src = photo.url;
    img.alt = photo.caption;
    img.loading = 'lazy';

    const caption = document.createElement('figcaption');
    caption.className = 'photo-strip__caption';
    caption.textContent = photo.caption;

    card.appendChild(img);
    card.appendChild(caption);
    track.appendChild(card);
  }

  el.appendChild(heading);
  el.appendChild(track);
  return el;
}
