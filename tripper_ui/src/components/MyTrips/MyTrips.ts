import "./MyTrips.css";
import {
  createTrip,
  ApiError,
  loadMyTrips,
  type NewTrip,
  type TripSummary,
} from "../../lib/trips";
import { renderGoogleSignIn, signOut } from "../../lib/auth";

function createInputField(
  labelText: string,
  name: string,
  type = "text",
  required = true,
): HTMLLabelElement {
  const label = document.createElement("label");
  label.textContent = labelText;

  const input = document.createElement("input");
  input.name = name;
  input.type = type;
  input.required = required;
  label.appendChild(input);
  return label;
}

function tripCard(trip: TripSummary): HTMLLIElement {
  const item = document.createElement("li");
  const link = document.createElement("a");
  link.className = "my-trips__card";
  link.href = `/tripper/trips/${encodeURIComponent(trip.id)}/edit`;
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
  descriptionInput.required = false;
  description.appendChild(descriptionInput);

  const coordinates = document.createElement("div");
  coordinates.className = "trip-form__coordinates";
  coordinates.append(
    createInputField("Latitude", "latitude", "number", false),
    createInputField("Longitude", "longitude", "number", false),
  );
  coordinates.querySelectorAll("input").forEach((input) => {
    input.step = "any";
  });

  const dates = document.createElement("div");
  dates.className = "trip-form__dates";
  dates.append(
    createInputField("Start date", "start_date", "date"),
    createInputField("End date", "end_date", "date"),
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
    createInputField("Trip name", "name"),
    createInputField("Short name", "short_name", "text", false),
    createInputField("Destination", "destination"),
    description,
    createInputField("Timezone", "timezone"),
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
    const latitude = String(data.get("latitude")).trim();
    const longitude = String(data.get("longitude")).trim();
    if (Boolean(latitude) !== Boolean(longitude)) {
      error.textContent = "Enter both latitude and longitude, or leave both blank.";
      save.disabled = false;
      return;
    }
    const trip: NewTrip = {
      name: String(data.get("name")),
      short_name: String(data.get("short_name")),
      destination: String(data.get("destination")),
      description: String(data.get("description")),
      timezone: String(data.get("timezone")),
      ...(latitude && longitude
        ? { location: { lat: Number(latitude), lng: Number(longitude) } }
        : {}),
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
  const signOutButton = document.createElement("button");
  signOutButton.className = "my-trips__button my-trips__button--secondary";
  signOutButton.type = "button";
  signOutButton.textContent = "Sign out";
  signOutButton.addEventListener("click", async () => {
    await signOut();
    await renderMyTrips(app);
  });
  const actions = document.createElement("div");
  actions.className = "my-trips__actions";
  actions.append(createButton, signOutButton);
  header.append(title, actions);

  const status = document.createElement("p");
  status.className = "my-trips__status";
  status.textContent = "Loading trips…";

  const list = document.createElement("ul");
  list.className = "my-trips__list";

  const addTrip = (trip: TripSummary): void => {
    status.remove();
    list.appendChild(tripCard(trip));
  };

  const dialog = newTripDialog((trip) => {
    window.location.assign(`/tripper/trips/${encodeURIComponent(trip.id)}/edit`);
  });
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
    if (caught instanceof ApiError && caught.status === 401) {
      createButton.remove();
      signOutButton.remove();
      status.className = "my-trips__sign-in";
      status.textContent = "Sign in with Google to see your trips.";
      const googleButton = document.createElement("div");
      page.insertBefore(googleButton, list);
      try {
        await renderGoogleSignIn(googleButton, () => void renderMyTrips(app));
      } catch (signInError) {
        status.className = "my-trips__status error-message";
        status.textContent =
          signInError instanceof Error
            ? signInError.message
            : "Google sign-in is unavailable.";
      }
      return;
    }
    status.className = "my-trips__status error-message";
    status.textContent =
      caught instanceof Error
        ? caught.message
        : "Something went wrong. Please try again.";
  }
}
