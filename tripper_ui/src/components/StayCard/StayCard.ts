import "./StayCard.css";
import { createMapButton } from "../MapButton";
import type { Stay } from "../../types";

export function createStayCard(stay: Stay): HTMLElement {
  const element = document.createElement("section");
  element.className = "stay-card";

  const icon = document.createElement("span");
  icon.className = "stay-card__icon";
  icon.textContent = "🏨";

  const info = document.createElement("div");
  info.className = "stay-card__info";
  const name = document.createElement("h4");
  name.className = "stay-card__name";
  name.textContent = stay.name;
  const address = document.createElement("p");
  address.className = "stay-card__address";
  address.textContent = stay.address;
  info.append(name, address);

  if (stay.check_in) {
    const checkIn = document.createElement("span");
    checkIn.className = "stay-card__badge";
    checkIn.textContent = `Check-in ${stay.check_in.slice(0, 5)}`;
    info.appendChild(checkIn);
  }
  if (stay.check_out) {
    const checkOut = document.createElement("span");
    checkOut.className = "stay-card__badge";
    checkOut.textContent = `Check-out ${stay.check_out.slice(0, 5)}`;
    info.appendChild(checkOut);
  }

  const actions = document.createElement("div");
  actions.className = "stay-card__actions";
  if (stay.location) {
    actions.appendChild(createMapButton(stay.location, stay.name));
  }
  if (stay.public_listing_url) {
    const bookingLink = document.createElement("a");
    bookingLink.className = "stay-card__booking";
    bookingLink.href = stay.public_listing_url;
    bookingLink.target = "_blank";
    bookingLink.rel = "noopener noreferrer";
    const platformIcon = document.createElement("span");
    platformIcon.className = "stay-card__booking-icon";
    platformIcon.textContent = stay.booking_platform === "airbnb" ? "🏠" : "🔖";
    const platformText = document.createElement("span");
    platformText.textContent =
      stay.booking_platform === "airbnb" ? "Airbnb" : "Booking.com";
    bookingLink.append(platformIcon, platformText);
    actions.appendChild(bookingLink);
  }

  element.append(icon, info, actions);
  return element;
}
