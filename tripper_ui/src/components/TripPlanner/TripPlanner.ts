import "./TripPlanner.css";
import {
  ApiError,
  loadParticipantTrip,
  updateTripDetails,
  type TripDetail,
  type TripDetailsUpdate,
} from "../../lib/trips";
import { loadCurrentAccount, renderGoogleSignIn } from "../../lib/auth";
import { clearTripDrafts, tripDraftKey } from "../../lib/drafts";

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

function recoveredDetailsDraft(key: string): TripDetailsDraft | undefined {
  const stored = sessionStorage.getItem(key);
  if (!stored) return undefined;
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
      return value as TripDetailsDraft;
    }
  } catch {
    sessionStorage.removeItem(key);
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
  let startingRevision = trip.revision;
  let draftStorageKey = tripDraftKey(
    accountId,
    trip.id,
    "trip_details",
    startingRevision,
  );
  const recovered = recoveredDetailsDraft(draftStorageKey);
  let draft = recovered ?? detailsDraft(trip);
  let dirty = recovered !== undefined;
  let activeSection: WorkspaceSection = recovered ? "details" : "plan";
  let saveCurrentForm: (() => Promise<boolean>) | undefined;

  const clearDraft = (): void => sessionStorage.removeItem(draftStorageKey);
  const persistDraft = (): void => {
    if (dirty) sessionStorage.setItem(draftStorageKey, JSON.stringify(draft));
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
    dirty = false;
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
  };

  const markDirty = (): void => {
    dirty = true;
    persistDraft();
    refreshPreview();
  };

  const showPlan = (): void => {
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
    const selectDate = (button: HTMLButtonElement, index: number): void => {
      dayNavigation
        .querySelectorAll("button")
        .forEach((candidate) => candidate.removeAttribute("aria-current"));
      button.setAttribute("aria-current", "date");
      const calendarDate = trip.calendar[index];
      const plan = trip.daily_plans.find(({ date }) => date === calendarDate.date);
      dayTitle.textContent = formatDateLabel(calendarDate.date);
      dayStatus.textContent = plan?.title || "Not planned yet";
    };
    trip.calendar.forEach((calendarDate, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = String(new Date(`${calendarDate.date}T00:00:00Z`).getUTCDate());
      button.setAttribute("aria-label", formatDateLabel(calendarDate.date));
      button.addEventListener("click", () => selectDate(button, index));
      dayNavigation.appendChild(button);
      if (index === 0) selectDate(button, index);
    });
    day.append(dayTitle, dayStatus);
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
      const latestName = document.createElement("p");
      latestName.textContent = latest.name;
      const latestRoute = document.createElement("p");
      latestRoute.textContent = latest.destinations.map(({ name }) => name).join(" → ");
      const latestDates = document.createElement("p");
      latestDates.textContent = `${latest.start_date} – ${latest.end_date}`;
      const explanation = document.createElement("p");
      explanation.textContent =
        "Your unsaved values are still in the form. Reload the saved values or deliberately reapply yours.";
      const conflictActions = document.createElement("div");
      conflictActions.className = "trip-details-form__conflict-actions";
      const reloadLatest = document.createElement("button");
      reloadLatest.type = "button";
      reloadLatest.textContent = "Reload latest";
      reloadLatest.addEventListener("click", () => {
        clearDraft();
        trip = latest;
        startingRevision = latest.revision;
        draftStorageKey = tripDraftKey(
          accountId,
          trip.id,
          "trip_details",
          startingRevision,
        );
        draft = detailsDraft(latest);
        dirty = false;
        refreshPreview();
        showDetails();
      });
      const reapply = document.createElement("button");
      reapply.type = "button";
      reapply.textContent = "Reapply my changes";
      reapply.addEventListener("click", () => {
        clearDraft();
        trip = latest;
        startingRevision = latest.revision;
        draftStorageKey = tripDraftKey(
          accountId,
          trip.id,
          "trip_details",
          startingRevision,
        );
        persistDraft();
        conflict.remove();
        summary.textContent = "Review your retained values, then retry the save.";
        save.textContent = "Retry save";
      });
      conflictActions.append(reloadLatest, reapply);
      conflict.append(
        conflictTitle,
        latestName,
        latestRoute,
        latestDates,
        explanation,
        conflictActions,
      );
      form.insertBefore(conflict, actions);
      summary.textContent = "This Trip changed after editing started.";
      save.textContent = "Retry save";
    };

    const makeReadOnlyAfterPermissionLoss = (): void => {
      permissionLost = true;
      clearTripDrafts(trip.id);
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
            clearTripDrafts();
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
        clearDraft();
        trip = savedTrip;
        startingRevision = trip.revision;
        draftStorageKey = tripDraftKey(
          accountId,
          trip.id,
          "trip_details",
          startingRevision,
        );
        draft = detailsDraft(trip);
        dirty = false;
        workspaceName.textContent = trip.name;
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
      clearTripDrafts(trip.id);
      renderReadOnlyWorkspace(app, trip);
      return;
    }
    document.title = `Plan ${trip.short_name || trip.name} · Tripper`;
    renderEditorWorkspace(app, trip, account.id);
  } catch (caught) {
    if (caught instanceof ApiError && [403, 404].includes(caught.status)) {
      clearTripDrafts(tripId);
    }
    loading.className = "error";
    loading.textContent =
      caught instanceof Error ? caught.message : "Could not load this trip.";
  }
}
