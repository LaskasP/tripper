import './NextDayButton.css';

export function createNextDayButton(nextDayNumber: number, onClick: () => void): HTMLElement {
  const btn = document.createElement('button');
  btn.className = 'next-day-btn';
  btn.type = 'button';
  btn.setAttribute('aria-label', `Go to day ${nextDayNumber}`);

  btn.innerHTML = `Next Day <span class="next-day-btn__chevron">↓</span>`;
  btn.addEventListener('click', onClick);

  return btn;
}
