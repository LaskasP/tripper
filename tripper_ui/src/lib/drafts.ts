const TRIP_DETAILS_DRAFT_PREFIX = "tripper:draft:trip_details:";
const DAILY_PLAN_DRAFT_PREFIX = "tripper:draft:daily_plan:";
const TIMELINE_ENTRY_DRAFT_PREFIX = "tripper:draft:timeline_entry:";
const PHOTO_DRAFT_PREFIX = "tripper:draft:photo:";

export function dailyPlanDraftPrefix(accountId: string, tripId: string): string {
  return `${DAILY_PLAN_DRAFT_PREFIX}${accountId}:${tripId}:`;
}

export function dailyPlanDraftKey(
  accountId: string, tripId: string, date: string, revision: number,
): string {
  return `${dailyPlanDraftPrefix(accountId, tripId)}${date}:${revision}`;
}

export function prepareDailyPlanDraftsForAccount(accountId: string): void {
  const accountPrefix = `${DAILY_PLAN_DRAFT_PREFIX}${accountId}:`;
  const keys: string[] = [];
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (key?.startsWith(DAILY_PLAN_DRAFT_PREFIX) && !key.startsWith(accountPrefix)) keys.push(key);
  }
  keys.forEach((key) => sessionStorage.removeItem(key));
}

export function clearDailyPlanDrafts(tripId?: string): void {
  const keys: string[] = [];
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (key?.startsWith(DAILY_PLAN_DRAFT_PREFIX) &&
        (tripId === undefined || key.split(":")[4] === tripId)) keys.push(key);
  }
  keys.forEach((key) => sessionStorage.removeItem(key));
}

export function timelineEntryDraftPrefix(accountId: string, tripId: string): string {
  return `${TIMELINE_ENTRY_DRAFT_PREFIX}${accountId}:${tripId}:`;
}

export function timelineEntryDraftKey(
  accountId: string,
  tripId: string,
  planId: string,
  entryId: string | undefined,
  startingRevision: number,
): string {
  return `${timelineEntryDraftPrefix(accountId, tripId)}${planId}:${entryId ?? "new"}:${startingRevision}`;
}

export function prepareTimelineEntryDraftsForAccount(accountId: string): void {
  const accountPrefix = `${TIMELINE_ENTRY_DRAFT_PREFIX}${accountId}:`;
  const keys: string[] = [];
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (key?.startsWith(TIMELINE_ENTRY_DRAFT_PREFIX) && !key.startsWith(accountPrefix)) keys.push(key);
  }
  keys.forEach((key) => sessionStorage.removeItem(key));
}

export function clearTimelineEntryDrafts(tripId?: string): void {
  const keys: string[] = [];
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (
      key?.startsWith(TIMELINE_ENTRY_DRAFT_PREFIX) &&
      (tripId === undefined || key.split(":")[4] === tripId)
    ) keys.push(key);
  }
  keys.forEach((key) => sessionStorage.removeItem(key));
}

export function photoDraftPrefix(accountId: string, tripId: string): string {
  return `${PHOTO_DRAFT_PREFIX}${accountId}:${tripId}:`;
}

export function photoDraftKey(
  accountId: string,
  tripId: string,
  planId: string,
  startingRevision: number,
): string {
  return `${photoDraftPrefix(accountId, tripId)}${planId}:${startingRevision}`;
}

export function preparePhotoDraftsForAccount(accountId: string): void {
  const accountPrefix = `${PHOTO_DRAFT_PREFIX}${accountId}:`;
  const keys: string[] = [];
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (key?.startsWith(PHOTO_DRAFT_PREFIX) && !key.startsWith(accountPrefix)) keys.push(key);
  }
  keys.forEach((key) => sessionStorage.removeItem(key));
}

export function clearPhotoDrafts(tripId?: string): void {
  const keys: string[] = [];
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (
      key?.startsWith(PHOTO_DRAFT_PREFIX) &&
      (tripId === undefined || key.split(":")[4] === tripId)
    ) keys.push(key);
  }
  keys.forEach((key) => sessionStorage.removeItem(key));
}

export function tripDetailsDraftPrefix(
  accountId: string,
  tripId: string,
): string {
  return `${TRIP_DETAILS_DRAFT_PREFIX}${accountId}:${tripId}:`;
}

export function tripDetailsDraftKey(
  accountId: string,
  tripId: string,
  startingRevision: number,
): string {
  return `${tripDetailsDraftPrefix(accountId, tripId)}${startingRevision}`;
}

export function prepareTripDetailsDraftsForAccount(accountId: string): void {
  const accountPrefix = `${TRIP_DETAILS_DRAFT_PREFIX}${accountId}:`;
  const obsoleteKeys: string[] = [];
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (
      key?.startsWith(TRIP_DETAILS_DRAFT_PREFIX) &&
      !key.startsWith(accountPrefix)
    ) {
      obsoleteKeys.push(key);
    }
  }
  obsoleteKeys.forEach((key) => sessionStorage.removeItem(key));
}

export function clearTripDetailsDrafts(tripId?: string): void {
  const matchingKeys: string[] = [];
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (
      key?.startsWith(TRIP_DETAILS_DRAFT_PREFIX) &&
      (tripId === undefined || key.split(":")[4] === tripId)
    ) {
      matchingKeys.push(key);
    }
  }
  matchingKeys.forEach((key) => sessionStorage.removeItem(key));
}
