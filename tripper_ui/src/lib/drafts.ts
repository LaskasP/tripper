const TRIP_DETAILS_DRAFT_PREFIX = "tripper:draft:trip_details:";

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
