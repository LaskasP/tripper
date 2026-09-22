import "./style.css";
import { renderParticipantGuide } from "./components/Guide";
import { renderMyTrips } from "./components/MyTrips";
import { renderTripPlanner } from "./components/TripPlanner";

async function main(): Promise<void> {
  const app = document.getElementById("app");
  if (!app) return;

  const path = window.location.pathname.replace(/\/$/, "");
  if (path.endsWith("/my-trips")) {
    await renderMyTrips(app);
    return;
  }
  const plannerRoute = path.match(/\/trips\/([^/]+)\/edit$/);
  if (plannerRoute) {
    await renderTripPlanner(app, decodeURIComponent(plannerRoute[1]));
    return;
  }
  const guideRoute = path.match(/\/trips\/([^/]+)$/);
  if (guideRoute) {
    await renderParticipantGuide(app, decodeURIComponent(guideRoute[1]));
    return;
  }

  // Draft guides have no anonymous root route. The public route arrives at cutover.
  await renderMyTrips(app);
}

void main();
