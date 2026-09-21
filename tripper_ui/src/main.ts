import './style.css';
import { loadTrip, loadDays } from './lib/data';
import { findTodayIndex } from './lib/time';
import { fetchWeather } from './lib/weather';
import { createDay } from './components/Day';
import { createAppHeader, updateAppHeader } from './components/AppHeader';
import { createDotNav, updateDotNav } from './components/DotNav';
import type { Day, TripConfig } from './types';
import { renderMyTrips, renderSelectedTrip } from './components/MyTrips';

async function main(): Promise<void> {
  const app = document.getElementById('app');
  if (!app) return;

  if (window.location.pathname.replace(/\/$/, '').endsWith('/my-trips')) {
    await renderMyTrips(app);
    return;
  }

  const selectedTripId = new URLSearchParams(window.location.search).get('trip');
  if (selectedTripId) {
    await renderSelectedTrip(app, selectedTripId);
    return;
  }

  // Loading state
  const loading = document.createElement('div');
  loading.className = 'loading';
  loading.textContent = 'Loading trip…';
  app.appendChild(loading);

  let trip: TripConfig;
  let days: Day[];
  try {
    [trip, days] = await Promise.all([loadTrip(), loadDays()]);
  } catch (err) {
    loading.className = 'error';
    loading.textContent = `Could not load trip data. ${err instanceof Error ? err.message : ''}`;
    return;
  }

  // Update page metadata from trip config
  document.title = trip.short_name;
  const metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc) metaDesc.setAttribute('content', trip.description);

  // Fetch weather from Open-Meteo API
  try {
    const weatherMap = await fetchWeather(
      trip.location.lat, trip.location.lng,
      trip.start_date, trip.end_date, trip.timezone,
    );
    for (const day of days) {
      const w = weatherMap.get(day.date);
      if (w) day.weather = w;
    }
  } catch {
    // Weather fetch failed — days without weather will show no chip
  }

  // Clear loading
  app.innerHTML = '';

  // Mount day sections
  const daySections: HTMLElement[] = [];
  for (let i = 0; i < days.length; i++) {
    const day = days[i];
    const isLastDay = i === days.length - 1;
    const section = createDay(day, {
      onNextDay: isLastDay ? undefined : () => {
        daySections[i + 1]?.scrollIntoView({ behavior: 'smooth' });
      },
    });
    daySections.push(section);
    app.appendChild(section);
  }

  // Mount header
  const header = createAppHeader(trip.name);
  document.body.appendChild(header);

  // Mount dot nav
  const dotNav = createDotNav(days.length, {
    onDotClick(index) {
      daySections[index]?.scrollIntoView({ behavior: 'smooth' });
    },
  });
  document.body.appendChild(dotNav);

  // Today button
  const todayIndex = findTodayIndex(days, trip.timezone);
  let todayBtn: HTMLButtonElement | null = null;

  if (todayIndex >= 0) {
    todayBtn = document.createElement('button');
    todayBtn.className = 'today-btn';
    todayBtn.type = 'button';
    todayBtn.textContent = '📍 Today';
    todayBtn.addEventListener('click', () => {
      daySections[todayIndex]?.scrollIntoView({ behavior: 'smooth' });
    });
    document.body.appendChild(todayBtn);
  }

  // IntersectionObserver for active day
  let activeIndex = 0;
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          const idx = daySections.indexOf(entry.target as HTMLElement);
          if (idx !== -1 && idx !== activeIndex) {
            activeIndex = idx;
            updateDotNav(dotNav, idx);
            updateAppHeader(header, days[idx].dayNumber, days[idx].date);

            // Show/hide today button
            if (todayBtn && todayIndex >= 0) {
              todayBtn.classList.toggle('today-btn--visible', idx !== todayIndex);
            }

            // Preload next day's background
            if (idx + 1 < days.length) {
              const img = new Image();
              img.src = days[idx + 1].backgroundImage;
            }
          }
        }
      }
    },
    { threshold: 0.5 },
  );

  for (const section of daySections) {
    observer.observe(section);
  }

  // Initialize header & dot nav with first day
  updateDotNav(dotNav, 0);
  updateAppHeader(header, days[0].dayNumber, days[0].date);

  // Overscroll-to-next-day detection for each day's inner scroll container
  for (let i = 0; i < daySections.length - 1; i++) {
    const scrollEl = daySections[i].querySelector<HTMLElement>('.day__scroll');
    const nextBtn = daySections[i].querySelector<HTMLElement>('.next-day-btn');
    if (!scrollEl) continue;

    let atBottom = false;
    let touchStartY = 0;

    // Track when user reaches the bottom of scrollable content
    scrollEl.addEventListener('scroll', () => {
      const isAtBottom = scrollEl.scrollTop + scrollEl.clientHeight >= scrollEl.scrollHeight - 2;
      if (isAtBottom !== atBottom) {
        atBottom = isAtBottom;
        nextBtn?.classList.toggle('next-day-btn--pulse', atBottom);
      }
    }, { passive: true });

    // Touch: detect continued upward swipe at bottom
    scrollEl.addEventListener('touchstart', (e) => {
      touchStartY = e.touches[0].clientY;
    }, { passive: true });

    scrollEl.addEventListener('touchmove', (e) => {
      if (!atBottom) return;
      const deltaY = touchStartY - e.touches[0].clientY;
      // User is swiping up (finger moving up) while already at bottom
      if (deltaY > 40) {
        atBottom = false;
        nextBtn?.classList.remove('next-day-btn--pulse');
        daySections[i + 1].scrollIntoView({ behavior: 'smooth' });
      }
    }, { passive: true });

    // Mouse wheel: detect continued scroll-down at bottom
    scrollEl.addEventListener('wheel', (e) => {
      if (!atBottom || e.deltaY <= 0) return;
      atBottom = false;
      nextBtn?.classList.remove('next-day-btn--pulse');
      daySections[i + 1].scrollIntoView({ behavior: 'smooth' });
    }, { passive: true });
  }

  // Auto-scroll to today if trip is in progress
  if (todayIndex >= 0) {
    requestAnimationFrame(() => {
      daySections[todayIndex].scrollIntoView({ behavior: 'instant' });
    });
  }
}

main();
