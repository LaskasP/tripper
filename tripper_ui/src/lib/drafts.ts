const TRIP_DRAFT_PREFIX = "tripper:draft:";

export function tripDraftKey(
  accountId: string,
  tripId: string,
  target: string,
  startingRevision: number,
): string {
  return `${TRIP_DRAFT_PREFIX}${accountId}:${tripId}:${target}:${startingRevision}`;
}

export function prepareTripDraftsForAccount(accountId: string): void {
  const accountPrefix = `${TRIP_DRAFT_PREFIX}${accountId}:`;
  const obsoleteKeys: string[] = [];
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (key?.startsWith(TRIP_DRAFT_PREFIX) && !key.startsWith(accountPrefix)) {
      obsoleteKeys.push(key);
    }
  }
  obsoleteKeys.forEach((key) => sessionStorage.removeItem(key));
}

export function clearTripDrafts(tripId?: string): void {
  const matchingKeys: string[] = [];
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (
      key?.startsWith(TRIP_DRAFT_PREFIX) &&
      (tripId === undefined || key.split(":")[3] === tripId)
    ) {
      matchingKeys.push(key);
    }
  }
  matchingKeys.forEach((key) => sessionStorage.removeItem(key));
}
