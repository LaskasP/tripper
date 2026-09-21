import "./MyTrips.css";
import {
  createTrip,
  loadMyTrips,
  loadPublicTrip,
  type NewTrip,
  type TripSummary,
} from "../../lib/trips";

function field(
  labelText: string,
  name: string,
  type = "text",
): HTMLLabelElement {
  const label = document.createElement("label");
  label.textContent = labelText;

  const input = document.createElement("input");
  input.name = name;
  input.type = type;
  input.required = true;
  label.appendChild(input);
  return label;
}

function tripCard(trip: TripSummary): HTMLLIElement {
  const item = document.createElement("li");
  const link = document.createElement("a");
  link.className = "my-trips__card";
  link.href = `/tripper/?trip=${encodeURIComponent(trip.id)}`;
  link.setAttribute(
    "aria-label",
    `${trip.name}, ${trip.destination}, ${trip.role}`,
  );

  const name = document.createElement("span");
  name.className = "my-trips__card-name";
  name.textContent = trip.name;

  const destination = document.createElement("span");
  destination.className = "my-trips__card-destination";
  destination.textContent = trip.destination;

  const dates = document.createElement("span");
  dates.className = "my-trips__card-dates";
  dates.textContent = `${trip.start_date} – ${trip.end_date}`;

  const role = document.createElement("span");
  role.className = "my-trips__role";
  role.textContent = trip.role[0].toUpperCase() + trip.role.slice(1);

  link.append(name, destination, dates, role);
  item.appendChild(link);
  return item;
}

function newTripDialog(
  onCreated: (trip: TripSummary) => void,
): HTMLDialogElement {
  const dialog = document.createElement("dialog");
  dialog.className = "trip-dialog";

  const form = document.createElement("form");
  form.className = "trip-form";
  form.method = "dialog";

  const title = document.createElement("h2");
  title.textContent = "Create a trip";

  const description = document.createElement("label");
  description.textContent = "Description";
  const descriptionInput = document.createElement("textarea");
  descriptionInput.name = "description";
  descriptionInput.required = true;
  description.appendChild(descriptionInput);

  const coordinates = document.createElement("div");
  coordinates.className = "trip-form__coordinates";
  coordinates.append(
    field("Latitude", "latitude", "number"),
    field("Longitude", "longitude", "number"),
  );
  coordinates.querySelectorAll("input").forEach((input) => {
    input.step = "any";
  });

  const dates = document.createElement("div");
  dates.className = "trip-form__dates";
  dates.append(
    field("Start date", "start_date", "date"),
    field("End date", "end_date", "date"),
  );

  const error = document.createElement("p");
  error.className = "error-message";
  error.setAttribute("role", "alert");

  const actions = document.createElement("div");
  actions.className = "trip-form__actions";
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.textContent = "Cancel";
  cancel.addEventListener("click", () => dialog.close());
  const save = document.createElement("button");
  save.type = "submit";
  save.textContent = "Save trip";
  actions.append(cancel, save);

  form.append(
    title,
    field("Trip name", "name"),
    field("Short name", "short_name"),
    field("Destination", "destination"),
    description,
    field("Timezone", "timezone"),
    coordinates,
    dates,
    error,
    actions,
  );

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    save.disabled = true;
    error.textContent = "";
    const data = new FormData(form);
    const trip: NewTrip = {
      name: String(data.get("name")),
      short_name: String(data.get("short_name")),
      destination: String(data.get("destination")),
      description: String(data.get("description")),
      timezone: String(data.get("timezone")),
      location: {
        lat: Number(data.get("latitude")),
        lng: Number(data.get("longitude")),
      },
      start_date: String(data.get("start_date")),
      end_date: String(data.get("end_date")),
    };

    try {
      const created = await createTrip(trip);
      dialog.close();
      form.reset();
      onCreated(created);
    } catch (caught) {
      error.textContent =
        caught instanceof Error
          ? caught.message
          : "Something went wrong. Please try again.";
    } finally {
      save.disabled = false;
    }
  });

  dialog.appendChild(form);
  return dialog;
}

export async function renderMyTrips(app: HTMLElement): Promise<void> {
  document.title = "My Trips · Tripper";
  document.documentElement.style.scrollSnapType = "none";

  const page = document.createElement("main");
  page.className = "my-trips";

  const header = document.createElement("header");
  header.className = "my-trips__header";
  const title = document.createElement("h1");
  title.className = "my-trips__title";
  title.textContent = "My Trips";
  const createButton = document.createElement("button");
  createButton.className = "my-trips__button";
  createButton.type = "button";
  createButton.textContent = "Create trip";
  header.append(title, createButton);

  const status = document.createElement("p");
  status.className = "my-trips__status";
  status.textContent = "Loading trips…";

  const list = document.createElement("ul");
  list.className = "my-trips__list";

  const addTrip = (trip: TripSummary): void => {
    status.remove();
    list.appendChild(tripCard(trip));
  };

  const dialog = newTripDialog(addTrip);
  createButton.addEventListener("click", () => dialog.showModal());
  page.append(header, status, list, dialog);
  app.replaceChildren(page);

  try {
    const trips = await loadMyTrips();
    if (trips.length === 0) {
      status.className = "my-trips__empty";
      status.textContent = "You have no trips yet.";
      return;
    }
    trips.forEach(addTrip);
  } catch (caught) {
    status.className = "my-trips__status error-message";
    status.textContent =
      caught instanceof Error
        ? caught.message
        : "Something went wrong. Please try again.";
  }
}

export async function renderSelectedTrip(
  app: HTMLElement,
  tripId: string,
): Promise<void> {
  document.documentElement.style.scrollSnapType = "none";
  const loading = document.createElement("p");
  loading.className = "loading";
  loading.textContent = "Loading trip…";
  app.replaceChildren(loading);

  try {
    const trip = await loadPublicTrip(tripId);
    document.title = trip.short_name;

    const page = document.createElement("main");
    page.className = "empty-trip";
    const destination = document.createElement("p");
    destination.className = "empty-trip__destination";
    destination.textContent = trip.destination;
    const title = document.createElement("h1");
    title.textContent = trip.name;
    const message = document.createElement("p");
    message.className = "empty-trip__message";
    message.textContent = "No days planned yet.";
    page.append(destination, title, message);
    app.replaceChildren(page);
  } catch (caught) {
    loading.className = "error";
    loading.textContent =
      caught instanceof Error ? caught.message : "Could not load this trip.";
  }
}
