import "./style.css";
import { renderParticipantGuide, renderPublicGuide } from "./components/Guide";
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
  const publicGuideRoute = path.match(/\/g\/([^/]+)$/);
  if (publicGuideRoute) {
    await renderPublicGuide(app, decodeURIComponent(publicGuideRoute[1]));
    return;
  }
  const guideRoute = path.match(/\/trips\/([^/]+)$/);
  if (guideRoute) {
    await renderParticipantGuide(app, decodeURIComponent(guideRoute[1]));
    return;
  }

  await renderMyTrips(app);
}

void main();
