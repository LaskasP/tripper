import './style.css';
import { loadTrip, loadDays } from './lib/data';
import { findTodayIndex } from './lib/time';
import { fetchWeather } from './lib/weather';
import { createDay } from './components/Day';
import { createAppHeader, updateAppHeader } from './components/AppHeader';
import { createDotNav, updateDotNav } from './components/DotNav';
import type { Day, TripConfig } from './types';

async function main(): Promise<void> {
  const app = document.getElementById('app');
  if (!app) return;

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
  document.title = trip.shortName;
  const metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc) metaDesc.setAttribute('content', trip.description);

  // Fetch weather from Open-Meteo API
  try {
    const weatherMap = await fetchWeather(
      trip.location.lat, trip.location.lng,
      trip.startDate, trip.endDate, trip.timezone,
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
  for (const day of days) {
    const section = createDay(day);
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

  // Auto-scroll to today if trip is in progress
  if (todayIndex >= 0) {
    requestAnimationFrame(() => {
      daySections[todayIndex].scrollIntoView({ behavior: 'instant' });
    });
  }
}

main();
