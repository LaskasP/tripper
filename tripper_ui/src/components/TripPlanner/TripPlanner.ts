import "./TripPlanner.css";
import { loadParticipantTrip } from "../../lib/trips";

function formatDateLabel(date: Date): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export async function renderTripPlanner(
  app: HTMLElement,
  tripId: string,
): Promise<void> {
  document.documentElement.style.scrollSnapType = "none";
  const loading = document.createElement("p");
  loading.className = "loading";
  loading.textContent = "Loading trip…";
  app.replaceChildren(loading);

  try {
    const trip = await loadParticipantTrip(tripId);
    document.title = `Plan ${trip.short_name || trip.name} · Tripper`;

    const page = document.createElement("main");
    page.className = "trip-planner";

    const back = document.createElement("a");
    back.className = "trip-planner__back";
    back.href = "/tripper/my-trips";
    back.textContent = "Back to My Trips";

    const eyebrow = document.createElement("p");
    eyebrow.className = "trip-planner__eyebrow";
    eyebrow.textContent = `${trip.name} · ${trip.destination}`;

    const title = document.createElement("h1");
    title.textContent = "Plan";

    const dayNavigation = document.createElement("nav");
    dayNavigation.className = "trip-planner__days";
    dayNavigation.setAttribute("aria-label", "Trip dates");

    const selectedDate = document.createElement("h2");
    const message = document.createElement("p");
    message.className = "trip-planner__unplanned";
    message.textContent = "Not planned yet";

    const showDate = (button: HTMLButtonElement, date: Date): void => {
      dayNavigation
        .querySelectorAll("button")
        .forEach((dateButton) => dateButton.removeAttribute("aria-current"));
      button.setAttribute("aria-current", "date");
      selectedDate.textContent = formatDateLabel(date);
    };

    trip.calendar.forEach((calendarDate, index) => {
      const date = new Date(`${calendarDate.date}T00:00:00Z`);
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = String(date.getUTCDate());
      button.setAttribute("aria-label", formatDateLabel(date));
      button.addEventListener("click", () => showDate(button, date));
      dayNavigation.appendChild(button);
      if (index === 0) showDate(button, date);
    });

    const emptyDay = document.createElement("section");
    emptyDay.className = "trip-planner__empty-day";
    emptyDay.append(selectedDate, message);

    const people = document.createElement("section");
    people.className = "trip-planner__people";
    const peopleTitle = document.createElement("h2");
    peopleTitle.textContent = "People";
    const roster = document.createElement("ul");
    roster.className = "trip-planner__roster";
    for (const participant of trip.roster) {
      const item = document.createElement("li");
      item.className = "trip-planner__roster-item";
      const name = document.createElement("span");
      name.textContent = participant.display_name;
      const role = document.createElement("span");
      role.className = "trip-planner__role";
      role.textContent =
        participant.role[0].toUpperCase() + participant.role.slice(1);
      item.append(name, role);
      roster.appendChild(item);
    }
    people.append(peopleTitle, roster);

    page.append(back, eyebrow, title, dayNavigation, emptyDay, people);
    app.replaceChildren(page);
  } catch (caught) {
    loading.className = "error";
    loading.textContent =
      caught instanceof Error ? caught.message : "Could not load this trip.";
  }
}
