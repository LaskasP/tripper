const TRIP_DETAILS_DRAFT_PREFIX = "tripper:draft:trip_details:";
const DAILY_PLAN_DRAFT_PREFIX = "tripper:draft:daily_plan:";

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
