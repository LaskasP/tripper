import "./TripPlanner.css";
import {
  ApiError,
  clearDailyPlan,
  createTimelineEntry,
  deleteTimelineEntry,
  loadParticipantTrip,
  moveDailyPlan,
  moveTimelineEntry,
  reorderTimelineEntries,
  updateTripDetails,
  updateTimelineEntry,
  writeDailyPlan,
  type TimelineEntryDetail,
  type TripDetail,
  type TripDetailsUpdate,
} from "../../lib/trips";
import { loadCurrentAccount, renderGoogleSignIn } from "../../lib/auth";
import {
  clearDailyPlanDrafts,
  clearTimelineEntryDrafts,
  dailyPlanDraftKey,
  dailyPlanDraftPrefix,
  clearTripDetailsDrafts,
  tripDetailsDraftKey,
  tripDetailsDraftPrefix,
  timelineEntryDraftKey,
  timelineEntryDraftPrefix,
} from "../../lib/drafts";

type WorkspaceSection = "plan" | "details" | "people" | "publish";

interface DestinationDraft {
  id?: string;
  name: string;
  timezone: string;
  latitude: string;
  longitude: string;
}

interface TripDetailsDraft {
  name: string;
  short_name: string;
  description: string;
  start_date: string;
  end_date: string;
  destinations: DestinationDraft[];
}

interface DailyPlanDraft {
  id?: string;
  date: string;
  destination_id: string;
  title: string;
  summary: string;
  background_image: string;
  starting_revision: number;
}

interface TimelineEntryDraft {
  id?: string;
  plan_id: string;
  starting_revision: number;
  collection_revision: number;
  destination_id: string;
  time: string;
  title: string;
  description: string;
  location_name: string;
}

function recoveredTimelineDraft(
  accountId: string,
  trip: TripDetail,
): TimelineEntryDraft | undefined {
  const prefix = timelineEntryDraftPrefix(accountId, trip.id);
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (!key?.startsWith(prefix)) continue;
    try {
      const value = JSON.parse(sessionStorage.getItem(key) || "") as TimelineEntryDraft;
      const plan = trip.daily_plans.find(({ id }) => id === value.plan_id);
      const entry = plan?.timeline.find(({ id }) => id === value.id);
      const revisionMatches = value.id
        ? entry?.revision === value.starting_revision
        : plan?.timeline_revision === value.starting_revision;
      if (plan && revisionMatches && typeof value.title === "string" && typeof value.time === "string") {
        return value;
      }
    } catch {
      // Invalid or stale drafts are removed below.
    }
    sessionStorage.removeItem(key);
  }
  return undefined;
}

function dailyPlanDraft(trip: TripDetail, date: string): DailyPlanDraft {
  const plan = trip.daily_plans.find((item) => item.date === date);
  return {
    ...(plan ? { id: plan.id } : {}),
    date,
    destination_id: plan?.destination_id ?? trip.destinations[0].id,
    title: plan?.title ?? "",
    summary: plan?.summary ?? "",
    background_image: plan?.background_image ?? "",
    starting_revision: plan?.revision ?? trip.content_revision,
  };
}

function recoveredDailyPlanDraft(
  accountId: string, trip: TripDetail,
): DailyPlanDraft | undefined {
  const prefix = dailyPlanDraftPrefix(accountId, trip.id);
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (!key?.startsWith(prefix)) continue;
    try {
      const value = JSON.parse(sessionStorage.getItem(key) || "") as DailyPlanDraft;
      if (trip.calendar.some(({ date }) => date === value.date) &&
          typeof value.title === "string" && typeof value.summary === "string" &&
          typeof value.background_image === "string" &&
          typeof value.starting_revision === "number") return value;
    } catch {
      sessionStorage.removeItem(key);
    }
  }
  return undefined;
}

function formatDateLabel(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function detailsDraft(trip: TripDetail): TripDetailsDraft {
  return {
    name: trip.name,
    short_name: trip.short_name,
    description: trip.description,
    start_date: trip.start_date,
    end_date: trip.end_date,
    destinations: trip.destinations.map((destination) => ({
      id: destination.id,
      name: destination.name,
      timezone: destination.timezone,
      latitude: destination.location ? String(destination.location.lat) : "",
      longitude: destination.location ? String(destination.location.lng) : "",
    })),
  };
}

interface RecoveredDetailsDraft {
  draft: TripDetailsDraft;
  key: string;
  starting_revision: number;
}

function recoveredDetailsDraft(
  accountId: string,
  tripId: string,
  currentRevision: number,
): RecoveredDetailsDraft | undefined {
  const prefix = tripDetailsDraftPrefix(accountId, tripId);
  const keys = Array.from({ length: sessionStorage.length }, (_, index) =>
    sessionStorage.key(index),
  ).filter((key): key is string => key?.startsWith(prefix) ?? false);
  keys.sort((left, right) => {
    const leftRevision = Number(left.slice(prefix.length));
    const rightRevision = Number(right.slice(prefix.length));
    if (leftRevision === currentRevision) return -1;
    if (rightRevision === currentRevision) return 1;
    return rightRevision - leftRevision;
  });
  for (const key of keys) {
    const stored = sessionStorage.getItem(key);
    const startingRevision = Number(key.slice(prefix.length));
    if (!stored || !Number.isInteger(startingRevision)) {
      sessionStorage.removeItem(key);
      continue;
    }
    try {
      const value = JSON.parse(stored) as Partial<TripDetailsDraft>;
      if (
        typeof value.name === "string" &&
        typeof value.short_name === "string" &&
        typeof value.description === "string" &&
        typeof value.start_date === "string" &&
        typeof value.end_date === "string" &&
        Array.isArray(value.destinations)
      ) {
        return {
          draft: value as TripDetailsDraft,
          key,
          starting_revision: startingRevision,
        };
      }
    } catch {
      sessionStorage.removeItem(key);
    }
  }
  return undefined;
}

function roleLabel(role: TripDetail["role"]): string {
  return role[0].toUpperCase() + role.slice(1);
}

function renderReadOnlyWorkspace(app: HTMLElement, trip: TripDetail): void {
  document.title = `${trip.name} · Tripper`;
  const page = document.createElement("main");
  page.className = "trip-planner trip-planner--read-only";
  const back = document.createElement("a");
  back.className = "trip-planner__back";
  back.href = "/tripper/my-trips";
  back.textContent = "Back to My Trips";
  const title = document.createElement("h1");
  title.textContent = trip.name;
  const notice = document.createElement("p");
  notice.className = "trip-planner__read-only-notice";
  notice.textContent = "Traveller access is read-only.";
  const summary = document.createElement("p");
  summary.textContent = `${trip.destinations.map(({ name }) => name).join(" → ")} · ${formatDateLabel(trip.start_date)} – ${formatDateLabel(trip.end_date)}`;
  const viewGuide = document.createElement("a");
  viewGuide.className = "trip-planner__primary-link";
  viewGuide.href = `/tripper/trips/${encodeURIComponent(trip.id)}`;
  viewGuide.textContent = "View guide";
  page.append(back, title, notice, summary, viewGuide);
  app.replaceChildren(page);
}

function createRoster(trip: TripDetail): HTMLElement {
  const section = document.createElement("section");
  section.className = "trip-planner__people";
  const title = document.createElement("h2");
  title.textContent = "People";
  const roster = document.createElement("ul");
  roster.className = "trip-planner__roster";
  for (const participant of trip.roster) {
    const item = document.createElement("li");
    item.className = "trip-planner__roster-item";
    const name = document.createElement("span");
    name.textContent = participant.display_name;
    const role = document.createElement("span");
    role.className = "trip-planner__role";
    role.textContent = roleLabel(participant.role);
    item.append(name, role);
    roster.appendChild(item);
  }
  section.append(title, roster);
  return section;
}

function renderEditorWorkspace(
  app: HTMLElement,
  initialTrip: TripDetail,
  accountId: string,
): void {
  let trip = initialTrip;
  const recovered = recoveredDetailsDraft(accountId, trip.id, trip.revision);
  const recoveredPlan = recoveredDailyPlanDraft(accountId, trip);
  const recoveredTimeline = recoveredTimelineDraft(accountId, trip);
  if (recovered && recoveredPlan) clearDailyPlanDrafts(trip.id);
  if ((recovered || recoveredPlan) && recoveredTimeline) clearTimelineEntryDrafts(trip.id);
  let startingRevision = recovered?.starting_revision ?? trip.revision;
  let draftStorageKey =
    recovered?.key ?? tripDetailsDraftKey(accountId, trip.id, startingRevision);
  let draft = recovered?.draft ?? detailsDraft(trip);
  let timelineDraft = recovered || recoveredPlan ? undefined : recoveredTimeline;
  const recoveredTimelinePlan = trip.daily_plans.find(({ id }) => id === timelineDraft?.plan_id);
  let planDraft = recoveredPlan ?? dailyPlanDraft(
    trip,
    recoveredTimelinePlan?.date ?? trip.calendar[0]?.date ?? trip.start_date,
  );
  let dirty = recovered !== undefined || recoveredPlan !== undefined || timelineDraft !== undefined;
  let activeSection: WorkspaceSection = recovered ? "details" : "plan";
  let saveCurrentForm: (() => Promise<boolean>) | undefined;

  const planStorageKey = (): string => dailyPlanDraftKey(
    accountId, trip.id, planDraft.date, planDraft.starting_revision,
  );
  const clearDraft = (): void => sessionStorage.removeItem(
    timelineDraft
      ? timelineEntryDraftKey(
          accountId,
          trip.id,
          timelineDraft.plan_id,
          timelineDraft.id,
          timelineDraft.starting_revision,
        )
      : activeSection === "plan" ? planStorageKey() : draftStorageKey,
  );
  const persistDraft = (): void => {
    if (!dirty) return;
    if (timelineDraft) {
      clearTimelineEntryDrafts(trip.id);
      sessionStorage.setItem(
        timelineEntryDraftKey(
          accountId,
          trip.id,
          timelineDraft.plan_id,
          timelineDraft.id,
          timelineDraft.starting_revision,
        ),
        JSON.stringify(timelineDraft),
      );
    } else if (activeSection === "plan") sessionStorage.setItem(planStorageKey(), JSON.stringify(planDraft));
    else sessionStorage.setItem(draftStorageKey, JSON.stringify(draft));
  };

  const page = document.createElement("main");
  page.className = "trip-planner trip-workspace";
  const header = document.createElement("header");
  header.className = "trip-workspace__header";
  const back = document.createElement("a");
  back.className = "trip-planner__back";
  back.href = "/tripper/my-trips";
  back.textContent = "Back to My Trips";
  const identity = document.createElement("div");
  const workspaceName = document.createElement("strong");
  workspaceName.textContent = trip.name;
  const access = document.createElement("span");
  access.textContent = roleLabel(trip.role);
  identity.append(workspaceName, access);
  const viewGuide = document.createElement("a");
  viewGuide.className = "trip-planner__view-guide";
  viewGuide.href = `/tripper/trips/${encodeURIComponent(trip.id)}`;
  viewGuide.textContent = "View guide";
  header.append(back, identity, viewGuide);

  const tabs = document.createElement("div");
  tabs.className = "trip-workspace__tabs";
  tabs.setAttribute("role", "tablist");
  const content = document.createElement("section");
  content.className = "trip-workspace__content";
  const preview = document.createElement("aside");
  preview.className = "trip-workspace__preview";
  preview.dataset.testid = "trip-preview";
  const layout = document.createElement("div");
  layout.className = "trip-workspace__layout";
  layout.append(content, preview);

  const navigationDialog = document.createElement("dialog");
  navigationDialog.className = "trip-navigation-dialog";
  navigationDialog.setAttribute("aria-labelledby", "unsaved-changes-title");
  const navigationTitle = document.createElement("h2");
  navigationTitle.id = "unsaved-changes-title";
  navigationTitle.textContent = "Unsaved changes";
  const navigationMessage = document.createElement("p");
  navigationMessage.textContent = "Save your changes before leaving this form?";
  const navigationActions = document.createElement("div");
  navigationActions.className = "trip-navigation-dialog__actions";
  const saveAndLeave = document.createElement("button");
  saveAndLeave.type = "button";
  saveAndLeave.textContent = "Save";
  const discardAndLeave = document.createElement("button");
  discardAndLeave.type = "button";
  discardAndLeave.textContent = "Discard";
  const keepEditing = document.createElement("button");
  keepEditing.type = "button";
  keepEditing.textContent = "Keep editing";
  navigationActions.append(saveAndLeave, discardAndLeave, keepEditing);
  navigationDialog.append(navigationTitle, navigationMessage, navigationActions);
  let pendingNavigation: (() => void) | undefined;
  const requestNavigation = (action: () => void): void => {
    if (!dirty) {
      action();
      return;
    }
    pendingNavigation = action;
    navigationDialog.showModal();
  };
  saveAndLeave.addEventListener("click", async () => {
    if (!saveCurrentForm || !(await saveCurrentForm())) return;
    navigationDialog.close();
    pendingNavigation?.();
  });
  discardAndLeave.addEventListener("click", () => {
    clearDraft();
    draft = detailsDraft(trip);
    planDraft = dailyPlanDraft(trip, planDraft.date);
    timelineDraft = undefined;
    dirty = false;
    refreshPreview();
    navigationDialog.close();
    pendingNavigation?.();
  });
  keepEditing.addEventListener("click", () => navigationDialog.close());
  back.addEventListener("click", (event) => {
    event.preventDefault();
    requestNavigation(() => window.location.assign(back.href));
  });
  viewGuide.addEventListener("click", (event) => {
    event.preventDefault();
    requestNavigation(() => window.location.assign(viewGuide.href));
  });

  const refreshPreview = (): void => {
    preview.replaceChildren();
    const label = document.createElement("p");
    label.className = "trip-workspace__preview-label";
    label.textContent = dirty ? "Unsaved preview" : "Saved guide preview";
    const title = document.createElement("h2");
    title.textContent = draft.name.trim() || "Untitled Trip";
    const route = document.createElement("p");
    route.className = "trip-workspace__preview-route";
    route.textContent =
      draft.destinations.map(({ name }) => name.trim()).filter(Boolean).join(" → ") ||
      "No destination";
    const dates = document.createElement("p");
    dates.textContent = `${draft.start_date || "Start date"} – ${draft.end_date || "End date"}`;
    const description = document.createElement("p");
    description.className = "trip-workspace__preview-description";
    description.textContent = draft.description || "No description yet.";
    preview.append(label, title, route, dates, description);
    if (activeSection === "plan") {
      const dayPreview = document.createElement("p");
      dayPreview.textContent = `${formatDateLabel(planDraft.date)} · ${planDraft.title || "No day title"} · ${planDraft.summary}`;
      preview.appendChild(dayPreview);
      if (timelineDraft) {
        const activityPreview = document.createElement("p");
        activityPreview.textContent = `${timelineDraft.time || "No time"} · ${timelineDraft.title || "No activity title"} · ${timelineDraft.description}`;
        preview.appendChild(activityPreview);
      }
    }
  };

  const markDirty = (): void => {
    dirty = true;
    persistDraft();
    refreshPreview();
  };

  const adoptServerTrip = (
    serverTrip: TripDetail,
    retainActiveDraft: boolean,
  ): void => {
    clearDraft();
    trip = serverTrip;
    startingRevision = serverTrip.revision;
    draftStorageKey = tripDetailsDraftKey(accountId, trip.id, startingRevision);
    if (!retainActiveDraft) draft = detailsDraft(serverTrip);
    workspaceName.textContent = serverTrip.name;
  };

  const showPlan = (): void => {
    saveCurrentForm = undefined;
    const panel = document.createElement("div");
    panel.className = "trip-workspace__panel";
    const title = document.createElement("h1");
    title.textContent = "Plan";
    const dayNavigation = document.createElement("nav");
    dayNavigation.className = "trip-planner__days";
    dayNavigation.setAttribute("aria-label", "Trip dates");
    const day = document.createElement("section");
    day.className = "trip-planner__empty-day";
    const dayTitle = document.createElement("h2");
    const dayStatus = document.createElement("p");
    dayStatus.className = "trip-planner__unplanned";
    const editor = document.createElement("div");
    editor.className = "trip-details-form";
    const renderEditor = (): void => {
      editor.replaceChildren();
      const current = trip.daily_plans.find(({ date }) => date === planDraft.date);
      const form = document.createElement("form");
      form.className = "trip-details-form";
      form.noValidate = true;
      const heading = document.createElement("h3");
      heading.textContent = current ? "Edit day" : "Create day";
      const validation = document.createElement("p");
      validation.setAttribute("role", "alert");
      const makeField = (labelText: string, value: string, update: (value: string) => void): HTMLLabelElement => {
        const label = document.createElement("label");
        label.textContent = labelText;
        const input = document.createElement("input");
        input.value = value;
        input.addEventListener("input", () => { update(input.value); markDirty(); });
        label.appendChild(input);
        return label;
      };
      const destination = document.createElement("label");
      destination.textContent = "Primary destination";
      const destinationSelect = document.createElement("select");
      for (const item of trip.destinations) {
        const option = document.createElement("option");
        option.value = item.id;
        option.textContent = item.name;
        destinationSelect.appendChild(option);
      }
      destinationSelect.value = planDraft.destination_id;
      destinationSelect.addEventListener("change", () => {
        planDraft.destination_id = destinationSelect.value;
        markDirty();
      });
      destination.appendChild(destinationSelect);
      const summary = document.createElement("label");
      summary.textContent = "Day summary";
      const summaryInput = document.createElement("textarea");
      summaryInput.value = planDraft.summary;
      summaryInput.rows = 4;
      summaryInput.addEventListener("input", () => {
        planDraft.summary = summaryInput.value;
        markDirty();
      });
      summary.appendChild(summaryInput);
      const background = makeField("Background image HTTPS URL", planDraft.background_image,
        (value) => (planDraft.background_image = value));
      const imagePreview = document.createElement("img");
      imagePreview.className = "trip-plan__image-preview";
      imagePreview.alt = "Background preview";
      const showImage = (): void => {
        imagePreview.hidden = !planDraft.background_image.startsWith("https://");
        if (!imagePreview.hidden) imagePreview.src = planDraft.background_image;
      };
      background.querySelector("input")?.addEventListener("input", showImage);
      imagePreview.addEventListener("error", () => { validation.textContent = "Background image could not be loaded."; });
      showImage();
      const actions = document.createElement("div");
      actions.className = "trip-details-form__actions";
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.textContent = "Cancel";
      cancel.addEventListener("click", () => {
        clearDraft(); dirty = false;
        planDraft = dailyPlanDraft(trip, planDraft.date);
        refreshPreview(); renderEditor();
      });
      const save = document.createElement("button");
      save.type = "submit";
      save.textContent = "Save plan";
      let conflictPending = false;
      actions.append(cancel, save);
      form.append(heading, validation, destination,
        makeField("Day title", planDraft.title, (value) => (planDraft.title = value)),
        summary, background, imagePreview, actions);
      const showPlanConflict = (
        latestTrip: TripDetail,
        retryOperation?: { label: string; after_date: string; run: (revision: number) => Promise<TripDetail> },
      ): void => {
        trip = latestTrip;
        conflictPending = true;
        save.disabled = true;
        form.querySelector(".trip-details-form__conflict")?.remove();
        const latest = trip.daily_plans.find(({ date }) => date === planDraft.date);
        const conflict = document.createElement("section");
        conflict.className = "trip-details-form__conflict";
        const heading = document.createElement("h4");
        heading.textContent = "Latest saved values";
        const fields = document.createElement("dl");
        for (const [label, value] of [
          ["Day title", latest?.title || "Not planned yet"],
          ["Day summary", latest?.summary || "None"],
          ["Background image", latest?.background_image || "None"],
          ["Primary destination", trip.destinations.find(({ id }) => id === latest?.destination_id)?.name || "None"],
        ]) {
          const term = document.createElement("dt");
          term.textContent = label;
          const detail = document.createElement("dd");
          detail.textContent = value;
          fields.append(term, detail);
        }
        const explanation = document.createElement("p");
        explanation.textContent = "Your unsaved values remain in the form. Reload saved values or deliberately reapply yours.";
        const choices = document.createElement("div");
        choices.className = "trip-details-form__conflict-actions";
        const reload = document.createElement("button");
        reload.type = "button";
        reload.textContent = "Reload latest";
        reload.addEventListener("click", () => {
          clearDraft(); dirty = false;
          planDraft = dailyPlanDraft(trip, planDraft.date);
          refreshPreview(); showPlan();
        });
        const reapply = document.createElement("button");
        reapply.type = "button";
        reapply.textContent = retryOperation?.label ?? "Reapply my changes";
        reapply.addEventListener("click", async () => {
          if (retryOperation) {
            if (!latest) {
              validation.textContent = "This plan was removed. Reload the latest guide.";
              return;
            }
            reapply.disabled = true;
            try {
              trip = await retryOperation.run(latest.revision);
              dirty = false;
              planDraft = dailyPlanDraft(trip, retryOperation.after_date);
              refreshPreview(); showPlan();
            } catch (error) {
              if (error instanceof ApiError && error.status === 409 && error.latest_values) {
                showPlanConflict(error.latest_values, retryOperation);
              } else validation.textContent = error instanceof Error ? error.message : "Could not retry. Reload and try again.";
            } finally { reapply.disabled = false; }
            return;
          }
          clearDraft();
          if (latest) planDraft.id = latest.id;
          else delete planDraft.id;
          planDraft.starting_revision = latest?.revision ?? trip.content_revision;
          dirty = true;
          persistDraft();
          conflictPending = false;
          save.disabled = false;
          conflict.remove();
          validation.textContent = "Review your retained values, then retry save.";
        });
        choices.append(reload, reapply);
        conflict.append(heading, fields, explanation, choices);
        form.insertBefore(conflict, actions);
        validation.textContent = "This Daily plan changed after editing started.";
      };
      const savePlan = async (): Promise<boolean> => {
        if (conflictPending) return false;
        validation.textContent = "";
        if (planDraft.background_image && !/^https:\/\/[^\s/]+/.test(planDraft.background_image)) {
          validation.textContent = "Enter an HTTPS background image URL.";
          background.querySelector("input")?.focus();
          return false;
        }
        save.disabled = true;
        try {
          const updated = await writeDailyPlan(trip.id, planDraft.date, {
            ...(planDraft.id ? { id: planDraft.id } : {}),
            starting_revision: planDraft.starting_revision,
            destination_id: planDraft.destination_id,
            title: planDraft.title,
            summary: planDraft.summary,
            background_image: planDraft.background_image,
          });
          clearDraft(); trip = updated; dirty = false;
          planDraft = dailyPlanDraft(trip, planDraft.date);
          refreshPreview(); showPlan();
          return true;
        } catch (error) {
          if (error instanceof ApiError && error.status === 409 && error.latest_values) {
            showPlanConflict(error.latest_values);
          } else if (error instanceof ApiError && error.status === 403) {
            clearDailyPlanDrafts(trip.id);
            form.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("input, textarea").forEach((input) => (input.readOnly = true));
            destinationSelect.disabled = true;
            editor.querySelectorAll<HTMLButtonElement>("button").forEach((button) => (button.disabled = true));
            validation.textContent = "Your editing permission changed. Your values remain available to copy.";
          } else if (error instanceof ApiError && error.status === 401) {
            validation.textContent = "Your Session expired. Sign in again to retry with these values.";
            const signIn = document.createElement("div");
            form.insertBefore(signIn, actions);
            void renderGoogleSignIn(signIn, () => {
              void (async () => {
                const account = await loadCurrentAccount();
                if (account.id !== accountId) {
                  clearDailyPlanDrafts();
                  window.location.assign("/tripper/my-trips");
                  return;
                }
                const latestTrip = await loadParticipantTrip(trip.id);
                if (latestTrip.role === "traveller") {
                  clearDailyPlanDrafts(trip.id);
                  validation.textContent = "Your editing permission changed. Your values remain available to copy.";
                  form.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("input, textarea").forEach((input) => (input.readOnly = true));
                  destinationSelect.disabled = true;
                  return;
                }
                trip = latestTrip;
                const latest = trip.daily_plans.find(({ date }) => date === planDraft.date);
                if (latest?.id !== planDraft.id ||
                    (latest?.revision ?? trip.content_revision) !== planDraft.starting_revision) {
                  showPlanConflict(trip);
                } else validation.textContent = "Signed in again. Retry save when ready.";
                signIn.remove();
              })().catch(() => { validation.textContent = "Could not restore your Session. Your values are still here."; });
            });
          } else {
            validation.textContent = error instanceof Error ? error.message : "Could not save plan. Retry.";
          }
          return false;
        } finally { save.disabled = conflictPending; }
      };
      saveCurrentForm = savePlan;
      form.addEventListener("submit", (event) => { event.preventDefault(); void savePlan(); });
      editor.append(form);
      if (planDraft.id !== current?.id ||
          planDraft.starting_revision !== (current?.revision ?? trip.content_revision)) {
        showPlanConflict(trip);
      }
      if (current) {
        const timeline = document.createElement("section");
        timeline.className = "timeline-editor";
        const timelineHeader = document.createElement("div");
        timelineHeader.className = "timeline-editor__header";
        const timelineTitle = document.createElement("h3");
        timelineTitle.textContent = "Timeline";
        const addActivity = document.createElement("button");
        addActivity.type = "button";
        addActivity.textContent = "Add activity";
        addActivity.hidden = timelineDraft !== undefined;
        addActivity.addEventListener("click", () => {
          if (dirty) {
            validation.textContent = "Save or Cancel your day changes before editing activities.";
            return;
          }
          timelineDraft = {
            plan_id: current.id,
            starting_revision: current.timeline_revision,
            collection_revision: current.timeline_revision,
            destination_id: "",
            time: "",
            title: "",
            description: "",
            location_name: "",
          };
          dirty = false;
          renderEditor();
        });
        timelineHeader.append(timelineTitle, addActivity);
        timeline.appendChild(timelineHeader);

        const showTimelineError = (error: unknown): void => {
          if (error instanceof ApiError && error.latest_values) trip = error.latest_values;
          validation.textContent = error instanceof Error
            ? `${error.message} Your activity values are still here.`
            : "Could not save the activity. Your values are still here.";
        };

        const renderActivityForm = (entry?: TimelineEntryDetail): HTMLElement => {
          if (!timelineDraft) throw new Error("Timeline draft is required");
          const activityDraft = timelineDraft;
          const activityForm = document.createElement("form");
          activityForm.className = "timeline-editor__form";
          activityForm.noValidate = true;
          const activityHeading = document.createElement("h4");
          activityHeading.textContent = entry ? "Edit activity" : "Add activity";
          const activityError = document.createElement("p");
          activityError.className = "trip-details-form__field-error";
          activityError.setAttribute("role", "alert");
          const activityField = (labelText: string, value: string, type = "text"): [HTMLLabelElement, HTMLInputElement] => {
            const label = document.createElement("label");
            label.textContent = labelText;
            const input = document.createElement("input");
            input.type = type;
            input.value = value;
            label.appendChild(input);
            return [label, input];
          };
          const [timeLabel, timeInput] = activityField("Activity time", activityDraft.time, "time");
          timeInput.required = true;
          const [titleLabel, titleInput] = activityField("Activity title", activityDraft.title);
          titleInput.required = true;
          const descriptionLabel = document.createElement("label");
          descriptionLabel.textContent = "Activity description";
          const descriptionInput = document.createElement("textarea");
          descriptionInput.rows = 3;
          descriptionInput.value = activityDraft.description;
          descriptionLabel.appendChild(descriptionInput);
          const [placeLabel, placeInput] = activityField("Activity place", activityDraft.location_name);
          const destinationLabel = document.createElement("label");
          destinationLabel.textContent = "Activity destination";
          const destinationInput = document.createElement("select");
          const primaryOption = document.createElement("option");
          primaryOption.value = "";
          primaryOption.textContent = `Use primary destination (${trip.destinations.find(({ id }) => id === current.destination_id)?.timezone ?? trip.timezone})`;
          destinationInput.appendChild(primaryOption);
          for (const item of trip.destinations) {
            const option = document.createElement("option");
            option.value = item.id;
            option.textContent = `${item.name} (${item.timezone})`;
            destinationInput.appendChild(option);
          }
          destinationInput.value = activityDraft.destination_id;
          destinationLabel.appendChild(destinationInput);
          const persistActivityInput = (): void => {
            activityDraft.time = timeInput.value;
            activityDraft.title = titleInput.value;
            activityDraft.description = descriptionInput.value;
            activityDraft.location_name = placeInput.value;
            activityDraft.destination_id = destinationInput.value;
            dirty = true;
            persistDraft();
            refreshPreview();
          };
          for (const input of [timeInput, titleInput, descriptionInput, placeInput, destinationInput]) {
            input.addEventListener("input", persistActivityInput);
            input.addEventListener("change", persistActivityInput);
          }
          const activityActions = document.createElement("div");
          activityActions.className = "timeline-editor__form-actions";
          const cancelActivity = document.createElement("button");
          cancelActivity.type = "button";
          cancelActivity.textContent = "Cancel activity";
          cancelActivity.addEventListener("click", () => {
            clearDraft();
            timelineDraft = undefined;
            dirty = false;
            refreshPreview();
            renderEditor();
          });
          const saveActivity = document.createElement("button");
          saveActivity.type = "submit";
          saveActivity.textContent = "Save activity";
          activityActions.append(cancelActivity, saveActivity);
          activityForm.append(
            activityHeading,
            activityError,
            timeLabel,
            titleLabel,
            descriptionLabel,
            placeLabel,
            destinationLabel,
            activityActions,
          );
          const makeActivityReadOnly = (): void => {
            clearTimelineEntryDrafts(trip.id);
            activityForm.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>(
              "input, textarea",
            ).forEach((input) => (input.readOnly = true));
            activityForm.querySelectorAll<HTMLSelectElement>("select")
              .forEach((input) => (input.disabled = true));
            editor.querySelectorAll<HTMLButtonElement>("button")
              .forEach((button) => (button.disabled = true));
            saveActivity.disabled = true;
          };
          const showActivityConflict = (latestTrip: TripDetail): void => {
            activityForm.querySelector(".trip-details-form__conflict")?.remove();
            const latestPlan = latestTrip.daily_plans.find(({ id }) => id === current.id);
            const latestEntry = latestPlan?.timeline.find(({ id }) => id === activityDraft.id);
            const conflict = document.createElement("section");
            conflict.className = "trip-details-form__conflict";
            const conflictTitle = document.createElement("h5");
            conflictTitle.textContent = "Latest saved activity";
            const latestValues = document.createElement("dl");
            for (const [label, value] of [
              ["Time", latestEntry?.time.slice(0, 5) ?? "Not saved"],
              ["Title", latestEntry?.title ?? "Not saved"],
              ["Description", latestEntry?.description || "None"],
              ["Place", latestEntry?.location_name || "None"],
            ]) {
              const term = document.createElement("dt");
              term.textContent = label;
              const detail = document.createElement("dd");
              detail.textContent = value;
              latestValues.append(term, detail);
            }
            const conflictActions = document.createElement("div");
            conflictActions.className = "trip-details-form__conflict-actions";
            const reload = document.createElement("button");
            reload.type = "button";
            reload.textContent = "Reload latest activity";
            reload.addEventListener("click", () => {
              clearDraft();
              timelineDraft = undefined;
              dirty = false;
              trip = latestTrip;
              refreshPreview();
              renderEditor();
            });
            const reapply = document.createElement("button");
            reapply.type = "button";
            reapply.textContent = "Reapply my activity";
            reapply.addEventListener("click", () => {
              trip = latestTrip;
              activityDraft.starting_revision = activityDraft.id
                ? latestEntry?.revision ?? activityDraft.starting_revision
                : latestPlan?.timeline_revision ?? activityDraft.starting_revision;
              activityDraft.collection_revision =
                latestPlan?.timeline_revision ?? activityDraft.collection_revision;
              dirty = true;
              persistDraft();
              conflict.remove();
              activityError.textContent = "Review your retained values, then retry Save activity.";
              saveActivity.disabled = false;
            });
            conflictActions.append(reload, reapply);
            conflict.append(conflictTitle, latestValues, conflictActions);
            activityForm.insertBefore(conflict, activityActions);
            saveActivity.disabled = true;
          };
          const saveTimelineEntry = async (): Promise<boolean> => {
            activityError.textContent = "";
            if (!timeInput.value) {
              activityError.textContent = "Enter a valid local time.";
              timeInput.focus();
              return false;
            }
            if (!titleInput.value.trim()) {
              activityError.textContent = "Enter an activity title.";
              titleInput.focus();
              return false;
            }
            saveActivity.disabled = true;
            const values = {
              destination_id: destinationInput.value || null,
              time: timeInput.value,
              title: titleInput.value,
              description: descriptionInput.value,
              location_name: placeInput.value || null,
            };
            const request = activityDraft.id
              ? updateTimelineEntry(
                  trip.id,
                  current.id,
                  activityDraft.id,
                  activityDraft.starting_revision,
                  values,
                )
              : createTimelineEntry(
                  trip.id,
                  current.id,
                  activityDraft.starting_revision,
                  values,
                );
            try {
              const updated = await request;
              clearDraft();
              trip = updated;
              timelineDraft = undefined;
              dirty = false;
              refreshPreview();
              window.setTimeout(renderEditor, 0);
              return true;
            } catch (error) {
              showTimelineError(error);
              activityError.textContent = error instanceof Error ? error.message : "Could not save activity.";
              if (error instanceof ApiError && error.status === 409 && error.latest_values) {
                showActivityConflict(error.latest_values);
                return false;
              } else if (error instanceof ApiError && error.status === 403) {
                makeActivityReadOnly();
                activityError.textContent = "Your editing permission changed. Your values remain available to copy.";
                return false;
              } else if (error instanceof ApiError && error.status === 401) {
                const signIn = document.createElement("div");
                activityForm.insertBefore(signIn, activityActions);
                activityError.textContent = "Your Session expired. Sign in again to retry with these values.";
                void renderGoogleSignIn(signIn, () => {
                  void (async () => {
                    const account = await loadCurrentAccount();
                    if (account.id !== accountId) {
                      clearTimelineEntryDrafts();
                      window.location.assign("/tripper/my-trips");
                      return;
                    }
                    const latestTrip = await loadParticipantTrip(trip.id);
                    if (latestTrip.role === "traveller") {
                      makeActivityReadOnly();
                      activityError.textContent = "Your editing permission changed. Your values remain available to copy.";
                      return;
                    }
                    trip = latestTrip;
                    const latestPlan = latestTrip.daily_plans.find(({ id }) => id === current.id);
                    const latestEntry = latestPlan?.timeline.find(({ id }) => id === activityDraft.id);
                    const revisionMatches = activityDraft.id
                      ? latestEntry?.revision === activityDraft.starting_revision
                      : latestPlan?.timeline_revision === activityDraft.starting_revision;
                    if (!revisionMatches) {
                      activityError.textContent = "This Timeline changed while your Session was expired.";
                      showActivityConflict(latestTrip);
                      signIn.remove();
                      return;
                    }
                    activityError.textContent = "Signed in again. Retry Save activity when ready.";
                    saveActivity.disabled = false;
                    signIn.remove();
                  })().catch(() => {
                    activityError.textContent = "Could not restore your Session. Your values are still here.";
                  });
                });
                return false;
              }
              saveActivity.disabled = false;
              return false;
            }
          };
          saveCurrentForm = saveTimelineEntry;
          activityForm.addEventListener("submit", (event) => {
            event.preventDefault();
            void saveTimelineEntry();
          });
          return activityForm;
        };

        if (timelineDraft && timelineDraft.plan_id === current.id) {
          const entry = timelineDraft.id
            ? current.timeline.find(({ id }) => id === timelineDraft?.id)
            : undefined;
          timeline.appendChild(renderActivityForm(entry));
        }
        const list = document.createElement("ol");
        list.className = "timeline-editor__list";
        current.timeline.forEach((entry, index) => {
          const item = document.createElement("li");
          item.className = "timeline-editor__item";
          const activitySummary = document.createElement("div");
          const activityName = document.createElement("strong");
          activityName.textContent = entry.title;
          const activityTime = document.createElement("span");
          activityTime.textContent = `${entry.time.slice(0, 5)} · ${entry.timezone}`;
          activitySummary.append(activityName, activityTime);
          const activityControls = document.createElement("div");
          activityControls.className = "timeline-editor__controls";
          const edit = document.createElement("button");
          edit.type = "button";
          edit.textContent = "Edit";
          edit.setAttribute("aria-label", `Edit ${entry.title}`);
          edit.addEventListener("click", () => {
            timelineDraft = {
              id: entry.id,
              plan_id: current.id,
              starting_revision: entry.revision,
              collection_revision: current.timeline_revision,
              destination_id: entry.destination_id ?? "",
              time: entry.time.slice(0, 5),
              title: entry.title,
              description: entry.description,
              location_name: entry.location_name ?? "",
            };
            dirty = false;
            renderEditor();
          });
          const up = document.createElement("button");
          up.type = "button";
          up.textContent = "Up";
          up.setAttribute("aria-label", `Move ${entry.title} up`);
          up.disabled = index === 0 || current.timeline[index - 1]?.time !== entry.time;
          const down = document.createElement("button");
          down.type = "button";
          down.textContent = "Down";
          down.setAttribute("aria-label", `Move ${entry.title} down`);
          down.disabled = index === current.timeline.length - 1 || current.timeline[index + 1]?.time !== entry.time;
          const reorder = (offset: number): void => {
            const ids = current.timeline.map(({ id }) => id);
            [ids[index], ids[index + offset]] = [ids[index + offset], ids[index]];
            void reorderTimelineEntries(trip.id, current.id, current.timeline_revision, ids)
              .then((updated) => { trip = updated; renderEditor(); refreshPreview(); })
              .catch(showTimelineError);
          };
          up.addEventListener("click", () => reorder(-1));
          down.addEventListener("click", () => reorder(1));
          const moveLabel = document.createElement("label");
          moveLabel.textContent = "Move to date";
          const moveSelect = document.createElement("select");
          moveSelect.setAttribute("aria-label", `Move ${entry.title} to date`);
          for (const targetPlan of trip.daily_plans.filter(({ id }) => id !== current.id)) {
            const option = document.createElement("option");
            option.value = targetPlan.date;
            option.textContent = formatDateLabel(targetPlan.date);
            moveSelect.appendChild(option);
          }
          moveLabel.appendChild(moveSelect);
          const moveActivity = document.createElement("button");
          moveActivity.type = "button";
          moveActivity.textContent = "Move";
          moveActivity.setAttribute("aria-label", `Move ${entry.title}`);
          moveActivity.disabled = moveSelect.options.length === 0;
          moveActivity.addEventListener("click", () => {
            const targetPlan = trip.daily_plans.find(({ date }) => date === moveSelect.value);
            if (!targetPlan) return;
            void moveTimelineEntry(
              trip.id,
              current.id,
              entry.id,
              current.timeline_revision,
              targetPlan.id,
              targetPlan.timeline_revision,
            ).then((updated) => { trip = updated; renderEditor(); refreshPreview(); })
              .catch(showTimelineError);
          });
          const remove = document.createElement("button");
          remove.type = "button";
          remove.textContent = "Remove";
          remove.setAttribute("aria-label", `Remove ${entry.title}`);
          remove.addEventListener("click", () => {
            void deleteTimelineEntry(
              trip.id, current.id, entry.id, entry.revision, current.timeline_revision,
            ).then((updated) => { trip = updated; renderEditor(); refreshPreview(); })
              .catch(showTimelineError);
          });
          activityControls.append(edit, up, down, moveLabel, moveActivity, remove);
          item.append(activitySummary, activityControls);
          list.appendChild(item);
        });
        list.hidden = timelineDraft !== undefined;
        timeline.appendChild(list);
        editor.appendChild(timeline);
        form.hidden = timelineDraft !== undefined;
      }
      if (current && !timelineDraft) {
        const move = document.createElement("label");
        move.textContent = "Move complete plan to";
        const target = document.createElement("select");
        for (const date of trip.calendar.filter(({ date }) => date !== current.date)) {
          const option = document.createElement("option");
          option.value = date.date;
          option.textContent = formatDateLabel(date.date) + (date.is_planned ? " (planned)" : "");
          target.appendChild(option);
        }
        move.appendChild(target);
        const moveButton = document.createElement("button");
        moveButton.type = "button";
        moveButton.textContent = "Move plan";
        moveButton.addEventListener("click", async () => {
          if (conflictPending) { validation.textContent = "Review the latest values before moving."; return; }
          if (dirty) { validation.textContent = "Save or Cancel your day changes before moving the plan."; return; }
          if (!target.value) return;
          try {
            trip = await moveDailyPlan(trip.id, current.id, target.value, current.revision);
            planDraft = dailyPlanDraft(trip, target.value);
            refreshPreview(); showPlan();
          } catch (error) {
            if (error instanceof ApiError && error.status === 409 && error.latest_values) {
              showPlanConflict(error.latest_values, {
                label: "Retry move",
                after_date: target.value,
                run: (revision) => moveDailyPlan(trip.id, current.id, target.value, revision),
              });
            } else validation.textContent = error instanceof Error ? error.message : "Move failed.";
          }
        });
        const clear = document.createElement("button");
        clear.type = "button";
        clear.textContent = "Clear plan";
        clear.addEventListener("click", async () => {
          if (conflictPending) { validation.textContent = "Review the latest values before clearing."; return; }
          if (dirty) { validation.textContent = "Save or Cancel your day changes before clearing the plan."; return; }
          if (!window.confirm(`Clear the complete plan for ${formatDateLabel(current.date)}? This removes its activities, stay, and photos.`)) return;
          try {
            trip = await clearDailyPlan(trip.id, current.date, current.revision);
            planDraft = dailyPlanDraft(trip, current.date);
            refreshPreview(); showPlan();
          } catch (error) {
            if (error instanceof ApiError && error.status === 409 && error.latest_values) {
              showPlanConflict(error.latest_values, {
                label: "Retry clear",
                after_date: current.date,
                run: (revision) => clearDailyPlan(trip.id, current.date, revision),
              });
            } else validation.textContent = error instanceof Error ? error.message : "Could not clear plan.";
          }
        });
        editor.append(move, moveButton, clear);
      }
    };
    const selectDate = (button: HTMLButtonElement, index: number): void => {
      dayNavigation
        .querySelectorAll("button")
        .forEach((candidate) => candidate.removeAttribute("aria-current"));
      button.setAttribute("aria-current", "date");
      const calendarDate = trip.calendar[index];
      const plan = trip.daily_plans.find(({ date }) => date === calendarDate.date);
      dayTitle.textContent = formatDateLabel(calendarDate.date);
      dayStatus.textContent = plan?.title || "Not planned yet";
      if (planDraft.date !== calendarDate.date) {
        planDraft = dailyPlanDraft(trip, calendarDate.date);
        dirty = false;
      }
      renderEditor();
      refreshPreview();
    };
    trip.calendar.forEach((calendarDate, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = String(new Date(`${calendarDate.date}T00:00:00Z`).getUTCDate());
      button.setAttribute("aria-label", formatDateLabel(calendarDate.date));
      button.addEventListener("click", () => {
        if (button.getAttribute("aria-current") === "date") return;
        requestNavigation(() => selectDate(button, index));
      });
      dayNavigation.appendChild(button);
      if (calendarDate.date === planDraft.date) selectDate(button, index);
    });
    day.append(dayTitle, dayStatus, editor);
    panel.append(title, dayNavigation, day, createRoster(trip));
    content.replaceChildren(panel);
  };

  const showPeople = (): void => content.replaceChildren(createRoster(trip));

  const showPublish = (): void => {
    const panel = document.createElement("div");
    panel.className = "trip-workspace__panel";
    const title = document.createElement("h1");
    title.textContent = "Publish";
    const description = document.createElement("p");
    description.className = "trip-workspace__placeholder";
    description.textContent = "This Trip is a private Draft. Publishing controls are not available yet.";
    panel.append(title, description);
    content.replaceChildren(panel);
  };

  const showDetails = (): void => {
    const form = document.createElement("form");
    form.className = "trip-details-form";
    form.noValidate = true;
    const title = document.createElement("h1");
    title.textContent = "Trip details";
    const summary = document.createElement("div");
    summary.className = "trip-details-form__summary";
    summary.setAttribute("role", "alert");

    const field = (
      labelText: string,
      validationKey: string | undefined,
      value: string,
      onInput: (value: string) => void,
      type = "text",
    ): HTMLLabelElement => {
      const label = document.createElement("label");
      label.textContent = labelText;
      const input = document.createElement("input");
      input.type = type;
      input.value = value;
      if (validationKey) input.dataset.validationKey = validationKey;
      input.addEventListener("input", () => {
        onInput(input.value);
        markDirty();
      });
      input.addEventListener("blur", () => {
        if (validationKey) validate(false);
      });
      const error = document.createElement("span");
      error.className = "trip-details-form__field-error";
      error.setAttribute("aria-live", "polite");
      label.append(input, error);
      return label;
    };

    const description = document.createElement("label");
    description.textContent = "Description";
    const descriptionInput = document.createElement("textarea");
    descriptionInput.rows = 4;
    descriptionInput.value = draft.description;
    descriptionInput.addEventListener("input", () => {
      draft.description = descriptionInput.value;
      markDirty();
    });
    description.appendChild(descriptionInput);

    const dates = document.createElement("div");
    dates.className = "trip-details-form__dates";
    dates.append(
      field("Start date", "start_date", draft.start_date, (value) => (draft.start_date = value), "date"),
      field("End date", "end_date", draft.end_date, (value) => (draft.end_date = value), "date"),
    );

    const destinationsTitle = document.createElement("div");
    destinationsTitle.className = "trip-details-form__section-title";
    const destinationsHeading = document.createElement("h2");
    destinationsHeading.textContent = "Destinations";
    const addDestination = document.createElement("button");
    addDestination.type = "button";
    addDestination.textContent = "Add destination";
    destinationsTitle.append(destinationsHeading, addDestination);
    const destinationList = document.createElement("div");
    destinationList.className = "trip-details-form__destinations";

    const renderDestinations = (): void => {
      destinationList.replaceChildren();
      draft.destinations.forEach((destination, index) => {
        const card = document.createElement("fieldset");
        card.className = "trip-details-form__destination";
        const legend = document.createElement("legend");
        legend.textContent = `Destination ${index + 1}`;
        const controls = document.createElement("div");
        controls.className = "trip-details-form__destination-actions";
        const moveUp = document.createElement("button");
        moveUp.type = "button";
        moveUp.textContent = "Move up";
        moveUp.disabled = index === 0;
        moveUp.setAttribute("aria-label", `Move ${destination.name || `destination ${index + 1}`} up`);
        moveUp.addEventListener("click", () => {
          moveDestination(index, index - 1);
        });
        const moveDown = document.createElement("button");
        moveDown.type = "button";
        moveDown.textContent = "Move down";
        moveDown.disabled = index === draft.destinations.length - 1;
        moveDown.setAttribute("aria-label", `Move ${destination.name || `destination ${index + 1}`} down`);
        moveDown.addEventListener("click", () => {
          moveDestination(index, index + 1);
        });
        const remove = document.createElement("button");
        remove.type = "button";
        remove.textContent = "Remove";
        remove.disabled = draft.destinations.length === 1;
        remove.addEventListener("click", () => {
          draft.destinations.splice(index, 1);
          markDirty();
          renderDestinations();
        });
        controls.append(moveUp, moveDown, remove);
        const nameField = field(
          `Destination ${index + 1} name`,
          `destination-${index}-name`,
          destination.name,
          (value) => {
            destination.name = value;
            const accessibleName = value || `destination ${index + 1}`;
            moveUp.setAttribute("aria-label", `Move ${accessibleName} up`);
            moveDown.setAttribute("aria-label", `Move ${accessibleName} down`);
          },
        );
        card.append(
          legend,
          controls,
          nameField,
          field(`Destination ${index + 1} timezone`, `destination-${index}-timezone`, destination.timezone, (value) => {
            destination.timezone = value;
          }),
        );
        const coordinates = document.createElement("div");
        coordinates.className = "trip-details-form__coordinates";
        coordinates.append(
          field(`Destination ${index + 1} latitude`, `destination-${index}-latitude`, destination.latitude, (value) => {
            destination.latitude = value;
          }, "number"),
          field(`Destination ${index + 1} longitude`, `destination-${index}-longitude`, destination.longitude, (value) => {
            destination.longitude = value;
          }, "number"),
        );
        coordinates.querySelectorAll("input").forEach((input) => (input.step = "any"));
        card.appendChild(coordinates);
        destinationList.appendChild(card);
      });
    };

    function moveDestination(from: number, to: number): void {
      const [destination] = draft.destinations.splice(from, 1);
      draft.destinations.splice(to, 0, destination);
      markDirty();
      renderDestinations();
    }

    addDestination.addEventListener("click", () => {
      draft.destinations.push({ name: "", timezone: "", latitude: "", longitude: "" });
      markDirty();
      renderDestinations();
      destinationList.querySelector<HTMLInputElement>("fieldset:last-child input")?.focus();
    });

    const actions = document.createElement("div");
    actions.className = "trip-details-form__actions";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.textContent = "Cancel";
    cancel.addEventListener("click", () => {
      clearDraft();
      draft = detailsDraft(trip);
      dirty = false;
      refreshPreview();
      showDetails();
    });
    const save = document.createElement("button");
    save.type = "submit";
    save.textContent = "Save changes";
    actions.append(cancel, save);

    form.append(
      title,
      summary,
      field("Trip name", "name", draft.name, (value) => (draft.name = value)),
      field("Short name", undefined, draft.short_name, (value) => (draft.short_name = value)),
      description,
      dates,
      destinationsTitle,
      destinationList,
      actions,
    );
    renderDestinations();

    function validate(focusFirst: boolean): boolean {
      const errors: Array<{ key: string; message: string }> = [];
      if (!draft.name.trim()) errors.push({ key: "name", message: "Trip name is required." });
      if (!draft.start_date) {
        errors.push({ key: "start_date", message: "Enter a start date." });
      } else if (!draft.end_date || draft.start_date > draft.end_date) {
        errors.push({ key: "end_date", message: "Enter an end date on or after the start date." });
      }
      draft.destinations.forEach((destination, index) => {
        if (!destination.name.trim()) {
          errors.push({
            key: `destination-${index}-name`,
            message: `Destination ${index + 1} needs a name.`,
          });
        }
        try {
          new Intl.DateTimeFormat("en-US", { timeZone: destination.timezone }).format();
        } catch {
          errors.push({
            key: `destination-${index}-timezone`,
            message: `Destination ${index + 1} needs a valid IANA timezone.`,
          });
        }
        const latitude = Number(destination.latitude);
        const longitude = Number(destination.longitude);
        const incomplete = Boolean(destination.latitude) !== Boolean(destination.longitude);
        const outOfRange =
          Boolean(destination.latitude) &&
          Boolean(destination.longitude) &&
          (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180);
        if (incomplete || outOfRange) {
          const coordinateKey =
            !destination.latitude || latitude < -90 || latitude > 90
              ? `destination-${index}-latitude`
              : `destination-${index}-longitude`;
          errors.push({
            key: coordinateKey,
            message: incomplete
              ? `Destination ${index + 1} needs both coordinates or neither.`
              : `Destination ${index + 1} coordinates are out of range.`,
          });
        }
      });
      const relevantInputs =
        form.querySelectorAll<HTMLInputElement>("[data-validation-key]");
      relevantInputs.forEach((input) => {
        const fieldError = input.nextElementSibling;
        if (fieldError instanceof HTMLElement) fieldError.textContent = "";
      });
      for (const error of errors) {
        const input = form.querySelector<HTMLInputElement>(
          `[data-validation-key="${error.key}"]`,
        );
        const fieldError = input?.nextElementSibling;
        if (fieldError instanceof HTMLElement) fieldError.textContent = error.message;
      }
      summary.textContent = errors.map(({ message }) => message).join(" ");
      if (focusFirst && errors[0]) {
        form
          .querySelector<HTMLInputElement>(`[data-validation-key="${errors[0].key}"]`)
          ?.focus();
      }
      return errors.length === 0;
    }

    let permissionLost = false;

    const showConflict = (latest: TripDetail): void => {
      form.querySelector(".trip-details-form__conflict")?.remove();
      const conflict = document.createElement("section");
      conflict.className = "trip-details-form__conflict";
      const conflictTitle = document.createElement("h2");
      conflictTitle.textContent = "Latest saved values";
      const latestFields = document.createElement("dl");
      const appendLatestField = (label: string, value: string): void => {
        const term = document.createElement("dt");
        term.textContent = label;
        const detail = document.createElement("dd");
        detail.textContent = value || "None";
        latestFields.append(term, detail);
      };
      appendLatestField("Trip name", latest.name);
      appendLatestField("Short name", latest.short_name);
      appendLatestField("Description", latest.description);
      appendLatestField("Start date", latest.start_date);
      appendLatestField("End date", latest.end_date);
      const destinationsTitle = document.createElement("h3");
      destinationsTitle.textContent = "Destinations";
      const latestDestinations = document.createElement("ol");
      latest.destinations.forEach((destination) => {
        const item = document.createElement("li");
        const location = destination.location
          ? `${destination.location.lat}, ${destination.location.lng}`
          : "No location";
        item.textContent = `${destination.name} — ${destination.timezone} — ${location}`;
        latestDestinations.appendChild(item);
      });
      const explanation = document.createElement("p");
      explanation.textContent =
        "Your unsaved values are still in the form. Reload the saved values or deliberately reapply yours.";
      const conflictActions = document.createElement("div");
      conflictActions.className = "trip-details-form__conflict-actions";
      const reloadLatest = document.createElement("button");
      reloadLatest.type = "button";
      reloadLatest.textContent = "Reload latest";
      reloadLatest.addEventListener("click", () => {
        adoptServerTrip(latest, false);
        dirty = false;
        refreshPreview();
        showDetails();
      });
      const reapply = document.createElement("button");
      reapply.type = "button";
      reapply.textContent = "Reapply my changes";
      reapply.addEventListener("click", () => {
        adoptServerTrip(latest, true);
        persistDraft();
        conflict.remove();
        summary.textContent = "Review your retained values, then retry the save.";
        save.textContent = "Retry save";
      });
      conflictActions.append(reloadLatest, reapply);
      conflict.append(
        conflictTitle,
        latestFields,
        destinationsTitle,
        latestDestinations,
        explanation,
        conflictActions,
      );
      form.insertBefore(conflict, actions);
      summary.textContent = "This Trip changed after editing started.";
      save.textContent = "Retry save";
    };

    const makeReadOnlyAfterPermissionLoss = (): void => {
      permissionLost = true;
      clearTripDetailsDrafts(trip.id);
      form.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("input, textarea")
        .forEach((control) => (control.readOnly = true));
      form.querySelectorAll<HTMLButtonElement>("button")
        .forEach((button) => (button.disabled = true));
      summary.textContent =
        "Your editing permission changed. Your values remain available to copy, but cannot be saved.";
    };

    const showSessionRecovery = (): void => {
      summary.textContent = "Your Session expired. Sign in again to keep these values and retry safely.";
      save.textContent = "Retry save";
      let signIn = form.querySelector<HTMLElement>(".trip-details-form__sign-in");
      if (signIn) return;
      signIn = document.createElement("div");
      signIn.className = "trip-details-form__sign-in";
      form.insertBefore(signIn, actions);
      void renderGoogleSignIn(signIn, () => {
        void (async () => {
          const currentAccount = await loadCurrentAccount();
          if (currentAccount.id !== accountId) {
            clearTripDetailsDrafts();
            clearDailyPlanDrafts();
            window.location.assign("/tripper/my-trips");
            return;
          }
          const latest = await loadParticipantTrip(trip.id);
          if (latest.role === "traveller") {
            makeReadOnlyAfterPermissionLoss();
            return;
          }
          signIn?.remove();
          if (latest.revision !== startingRevision) {
            showConflict(latest);
            return;
          }
          summary.textContent = "Signed in again. Retry save when ready.";
        })().catch(() => {
          summary.textContent = "Could not restore your Session. Your values are still here.";
        });
      }).catch(() => {
        summary.textContent = "Google sign-in is unavailable. Your values are still here.";
      });
    };

    const saveDetails = async (): Promise<boolean> => {
      if (!validate(true)) return false;
      summary.textContent = "Saving…";
      save.disabled = true;
      const request: TripDetailsUpdate = {
        starting_revision: startingRevision,
        name: draft.name,
        short_name: draft.short_name,
        description: draft.description,
        start_date: draft.start_date,
        end_date: draft.end_date,
        destinations: draft.destinations.map((destination) => ({
          ...(destination.id ? { id: destination.id } : {}),
          name: destination.name,
          timezone: destination.timezone,
          location:
            destination.latitude && destination.longitude
              ? { lat: Number(destination.latitude), lng: Number(destination.longitude) }
              : null,
        })),
      };
      try {
        const savedTrip = await updateTripDetails(trip.id, request);
        adoptServerTrip(savedTrip, false);
        dirty = false;
        refreshPreview();
        showDetails();
        const saved = document.createElement("p");
        saved.className = "trip-details-form__saved";
        saved.setAttribute("role", "status");
        saved.textContent = "Changes saved";
        content.prepend(saved);
        return true;
      } catch (caught) {
        if (caught instanceof ApiError && caught.code === "trip_revision_conflict" && caught.latest_values) {
          showConflict(caught.latest_values);
        } else if (caught instanceof ApiError && caught.status === 401) {
          showSessionRecovery();
        } else if (caught instanceof ApiError && caught.status === 403) {
          makeReadOnlyAfterPermissionLoss();
        } else {
          summary.textContent =
            caught instanceof Error ? `${caught.message} Retry when ready.` : "Could not save changes. Retry.";
          save.textContent = "Retry save";
        }
        return false;
      } finally {
        if (!permissionLost) save.disabled = false;
      }
    };
    saveCurrentForm = saveDetails;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void saveDetails();
    });
    content.replaceChildren(form);
    if (startingRevision !== trip.revision) showConflict(trip);
  };

  const sections: Array<[WorkspaceSection, string, () => void]> = [
    ["plan", "Plan", showPlan],
    ["details", "Trip details", showDetails],
    ["people", "People", showPeople],
    ...(trip.role === "creator"
      ? ([["publish", "Publish", showPublish]] as Array<[
          WorkspaceSection,
          string,
          () => void,
        ]>)
      : []),
  ];
  for (const [key, label, render] of sections) {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.setAttribute("role", "tab");
    tab.textContent = label;
    tab.addEventListener("click", () => {
      if (activeSection === key) return;
      requestNavigation(() => {
        activeSection = key;
        tabs.querySelectorAll("button").forEach((button) => {
          button.setAttribute("aria-selected", String(button === tab));
        });
        render();
      });
    });
    tab.setAttribute("aria-selected", String(activeSection === key));
    tabs.appendChild(tab);
  }

  page.append(header, tabs, layout, navigationDialog);
  app.replaceChildren(page);
  window.addEventListener("beforeunload", (event) => {
    if (!dirty) return;
    event.preventDefault();
  });
  refreshPreview();
  if (recovered) showDetails();
  else showPlan();
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
    const [account, trip] = await Promise.all([
      loadCurrentAccount(),
      loadParticipantTrip(tripId),
    ]);
    if (trip.role === "traveller") {
      clearTripDetailsDrafts(trip.id);
      clearDailyPlanDrafts(trip.id);
      renderReadOnlyWorkspace(app, trip);
      return;
    }
    document.title = `Plan ${trip.short_name || trip.name} · Tripper`;
    renderEditorWorkspace(app, trip, account.id);
  } catch (caught) {
    if (caught instanceof ApiError && [403, 404].includes(caught.status)) {
      clearTripDetailsDrafts(tripId);
      clearDailyPlanDrafts(tripId);
    }
    loading.className = "error";
    loading.textContent =
      caught instanceof Error ? caught.message : "Could not load this trip.";
  }
}
