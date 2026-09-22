import { createAppHeader, updateAppHeader } from "../AppHeader";
import { createDay } from "../Day";
import { createDotNav, updateDotNav } from "../DotNav";
import type { TripDetail } from "../../lib/trips";
import { loadParticipantTrip } from "../../lib/trips";
import { findTodayIndex } from "../../lib/time";
import { fetchWeather } from "../../lib/weather";
import type { Day } from "../../types";

function guideDays(trip: TripDetail): Day[] {
  return trip.daily_plans.map((plan) => ({
    date: plan.date,
    day_number: plan.day_number,
    title: plan.title,
    summary: plan.summary,
    background_image: plan.background_image,
    ...(plan.stay
      ? {
          stay: {
            name: plan.stay.name,
            address: plan.stay.address,
            ...(plan.stay.location ? { location: plan.stay.location } : {}),
            ...(plan.stay.check_in ? { check_in: plan.stay.check_in } : {}),
            ...(plan.stay.check_out ? { check_out: plan.stay.check_out } : {}),
            ...(plan.stay.public_listing_url
              ? { public_listing_url: plan.stay.public_listing_url }
              : {}),
            ...(plan.stay.booking_platform
              ? { booking_platform: plan.stay.booking_platform }
              : {}),
          },
        }
      : {}),
    timeline: plan.timeline.map((entry) => ({
      time: entry.time,
      title: entry.title,
      description: entry.description,
      ...(entry.location ? { location: entry.location } : {}),
      ...(entry.location_name ? { location_name: entry.location_name } : {}),
    })),
    photos: plan.photos,
  }));
}

export async function renderGuide(app: HTMLElement, trip: TripDetail): Promise<void> {
  const days = guideDays(trip);
  if (days.length === 0) {
    throw new Error("This trip has no planned days yet.");
  }
  document.documentElement.style.scrollSnapType = "y mandatory";
  document.title = trip.short_name || trip.name;
  const metaDescription = document.querySelector('meta[name="description"]');
  metaDescription?.setAttribute("content", trip.description);

  if (trip.location) {
    try {
      const weather = await fetchWeather(
        trip.location.lat,
        trip.location.lng,
        trip.start_date,
        trip.end_date,
        trip.timezone,
      );
      for (const day of days) {
        const forecast = weather.get(day.date);
        if (forecast) day.weather = forecast;
      }
    } catch {
      // Weather is derived and optional; canonical guide content remains available.
    }
  }

  app.replaceChildren();
  const daySections = days.map((day, index) => {
    const section = createDay(day, {
      onNextDay:
        index === days.length - 1
          ? undefined
          : () => daySections[index + 1]?.scrollIntoView({ behavior: "smooth" }),
    });
    app.appendChild(section);
    return section;
  });
  const header = createAppHeader(trip.name);
  document.body.appendChild(header);
  const dotNavigation = createDotNav(days.length, {
    onDotClick: (index) =>
      daySections[index]?.scrollIntoView({ behavior: "smooth" }),
  });
  document.body.appendChild(dotNavigation);

  const todayIndex = findTodayIndex(days, trip.timezone);
  let todayButton: HTMLButtonElement | null = null;
  if (todayIndex >= 0) {
    todayButton = document.createElement("button");
    todayButton.className = "today-btn";
    todayButton.type = "button";
    todayButton.textContent = "📍 Today";
    todayButton.addEventListener("click", () =>
      daySections[todayIndex]?.scrollIntoView({ behavior: "smooth" }),
    );
    document.body.appendChild(todayButton);
  }
  let activeIndex = 0;
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const index = daySections.indexOf(entry.target as HTMLElement);
        if (index < 0 || index === activeIndex) continue;
        activeIndex = index;
        updateDotNav(dotNavigation, index);
        updateAppHeader(header, days[index].day_number, days[index].date);
        todayButton?.classList.toggle(
          "today-btn--visible",
          index !== todayIndex,
        );
        if (index + 1 < days.length) {
          const image = new Image();
          image.src = days[index + 1].background_image;
        }
      }
    },
    { threshold: 0.5 },
  );
  daySections.forEach((section) => observer.observe(section));
  updateDotNav(dotNavigation, 0);
  updateAppHeader(header, days[0].day_number, days[0].date);

  for (let index = 0; index < daySections.length - 1; index += 1) {
    const scrollElement =
      daySections[index].querySelector<HTMLElement>(".day__scroll");
    const nextButton =
      daySections[index].querySelector<HTMLElement>(".next-day-btn");
    if (!scrollElement) continue;
    let atBottom = false;
    let touchStartY = 0;
    scrollElement.addEventListener(
      "scroll",
      () => {
        atBottom =
          scrollElement.scrollTop + scrollElement.clientHeight >=
          scrollElement.scrollHeight - 2;
        nextButton?.classList.toggle("next-day-btn--pulse", atBottom);
      },
      { passive: true },
    );
    scrollElement.addEventListener(
      "touchstart",
      (event) => {
        touchStartY = event.touches[0].clientY;
      },
      { passive: true },
    );
    scrollElement.addEventListener(
      "touchmove",
      (event) => {
        if (!atBottom || touchStartY - event.touches[0].clientY <= 40) return;
        atBottom = false;
        nextButton?.classList.remove("next-day-btn--pulse");
        daySections[index + 1].scrollIntoView({ behavior: "smooth" });
      },
      { passive: true },
    );
    scrollElement.addEventListener(
      "wheel",
      (event) => {
        if (!atBottom || event.deltaY <= 0) return;
        atBottom = false;
        nextButton?.classList.remove("next-day-btn--pulse");
        daySections[index + 1].scrollIntoView({ behavior: "smooth" });
      },
      { passive: true },
    );
  }
  if (todayIndex >= 0) {
    requestAnimationFrame(() =>
      daySections[todayIndex].scrollIntoView({ behavior: "instant" }),
    );
  }
}

export async function renderParticipantGuide(
  app: HTMLElement,
  tripId: string,
): Promise<void> {
  const loading = document.createElement("p");
  loading.className = "loading";
  loading.textContent = "Loading trip…";
  app.replaceChildren(loading);
  try {
    await renderGuide(app, await loadParticipantTrip(tripId));
  } catch (caught) {
    loading.className = "error";
    loading.textContent =
      caught instanceof Error ? caught.message : "Could not load this trip.";
  }
}
