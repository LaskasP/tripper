import './DotNav.css';

export interface DotNavCallbacks {
  onDotClick: (index: number) => void;
}

export function createDotNav(count: number, callbacks: DotNavCallbacks): HTMLElement {
  const nav = document.createElement('nav');
  nav.className = 'dot-nav';
  nav.setAttribute('aria-label', 'Day navigation');

  for (let i = 0; i < count; i++) {
    const dot = document.createElement('button');
    dot.className = 'dot-nav__dot';
    dot.type = 'button';
    dot.setAttribute('aria-label', `Go to day ${i + 1}`);
    dot.dataset.index = String(i);
    dot.addEventListener('click', () => callbacks.onDotClick(i));
    nav.appendChild(dot);
  }

  return nav;
}

export function updateDotNav(nav: HTMLElement, activeIndex: number): void {
  const dots = nav.querySelectorAll<HTMLElement>('.dot-nav__dot');
  dots.forEach((dot, i) => {
    dot.classList.toggle('dot-nav__dot--active', i === activeIndex);
    dot.setAttribute('aria-current', i === activeIndex ? 'true' : 'false');
  });
}
