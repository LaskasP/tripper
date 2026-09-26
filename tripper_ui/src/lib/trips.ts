export type TripRole = "creator" | "contributor" | "traveller";

export interface TripSummary {
  id: string;
  name: string;
  destination: string;
  short_name: string;
  start_date: string;
  end_date: string;
  role: TripRole;
}

export interface NewTrip {
  name: string;
  destination: string;
  short_name?: string;
  description?: string;
  timezone: string;
  location?: { lat: number; lng: number };
  start_date: string;
  end_date: string;
}

export interface TimelineEntryDetail {
  id: string;
  destination_id: string | null;
  revision: number;
  position: number;
  time: string;
  timezone: string;
  title: string;
  description: string;
  location: { lat: number; lng: number } | null;
  location_name: string | null;
}

export interface TimelineEntryWrite {
  destination_id?: string | null;
  time: string;
  title: string;
  description?: string;
  location_name?: string | null;
  location?: { lat: number; lng: number } | null;
}

export interface PhotoDetail {
  id: string;
  position: number;
  url: string;
  caption: string;
}

export interface StayDetail {
  id: string;
  revision: number;
  name: string;
  address: string;
  location: { lat: number; lng: number } | null;
  check_in: string | null;
  check_out: string | null;
  public_listing_url: string | null;
  booking_platform: "booking.com" | "airbnb" | null;
}

export interface StayWrite {
  id?: string;
  starting_revision: number;
  name: string;
  address?: string;
  location?: { lat: number; lng: number } | null;
  check_in?: string | null;
  check_out?: string | null;
  public_listing_url?: string | null;
  booking_platform?: "booking.com" | "airbnb" | null;
}

export interface GuideDetail {
  name: string;
  destination: string;
  short_name: string;
  description: string;
  timezone: string;
  location: { lat: number; lng: number } | null;
  start_date: string;
  end_date: string;
  calendar: Array<{
    date: string;
    day_number: number;
    is_planned: boolean;
  }>;
  daily_plans: Array<{
    date: string;
    day_number: number;
    title: string;
    summary: string;
    background_image: string;
    stay: Omit<StayDetail, "id" | "revision"> | null;
    timeline: Array<
      Omit<TimelineEntryDetail, "id" | "destination_id" | "revision" | "position">
    >;
    photos: Array<Pick<PhotoDetail, "url" | "caption">>;
  }>;
}

export interface TripDetail extends GuideDetail {
  id: string;
  revision: number;
  content_revision: number;
  role: TripRole;
  name: string;
  destination: string;
  short_name: string;
  description: string;
  timezone: string;
  location: { lat: number; lng: number } | null;
  start_date: string;
  end_date: string;
  destinations: Array<{
    id: string;
    name: string;
    timezone: string;
    location: { lat: number; lng: number } | null;
    position: number;
    revision: number;
  }>;
  calendar: Array<{
    date: string;
    day_number: number;
    is_planned: boolean;
  }>;
  daily_plans: Array<{
    id: string;
    destination_id: string;
    revision: number;
    timeline_revision: number;
    photo_revision: number;
    date: string;
    day_number: number;
    title: string;
    summary: string;
    background_image: string;
    stay: StayDetail | null;
    timeline: TimelineEntryDetail[];
    photos: PhotoDetail[];
  }>;
  roster: Array<{
    display_name: string;
    role: TripRole;
  }>;
}

export interface TripDetailsUpdate {
  starting_revision: number;
  name: string;
  short_name: string;
  description: string;
  start_date: string;
  end_date: string;
  destinations: Array<{
    id?: string;
    name: string;
    timezone: string;
    location: { lat: number; lng: number } | null;
  }>;
}

export interface DailyPlanWrite {
  id?: string;
  starting_revision: number;
  destination_id: string;
  title: string;
  summary: string;
  background_image: string;
}

export interface PublicationState {
  is_published: boolean;
  public_token: string | null;
  revision: number;
}

export interface DailyPlanResponse {
  id: string;
  destination_id: string;
  revision: number;
  date: string;
  title: string;
  summary: string;
  background_image: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly latest_values?: TripDetail;
  readonly current_plan?: DailyPlanResponse | null;
  readonly current_stay?: StayDetail | null;

  constructor(
    status: number,
    code: string,
    message: string,
    latestValues?: TripDetail,
    currentPlan?: DailyPlanResponse | null,
    currentStay?: StayDetail | null,
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.latest_values = latestValues;
    this.current_plan = currentPlan;
    this.current_stay = currentStay;
  }
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const csrf = init?.method && init.method !== "GET" ? sessionCsrfToken() : undefined;
  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      error?: {
        code?: string;
        message?: string;
        latest_values?: TripDetail;
        current_plan?: DailyPlanResponse | null;
        current_stay?: StayDetail | null;
      };
    } | null;
    throw new ApiError(
      response.status,
      body?.error?.code ?? `http_${response.status}`,
      response.status === 401
        ? "Sign in to manage your trips."
        : (body?.error?.message ?? "Something went wrong. Please try again."),
      body?.error?.latest_values,
      body?.error?.current_plan,
      body?.error?.current_stay,
    );
  }

  if (response.status === 204) return undefined as T;

  return (await response.json()) as T;
}

export function loadMyTrips(): Promise<TripSummary[]> {
  return apiRequest<TripSummary[]>("/api/me/trips");
}

export function createTrip(trip: NewTrip): Promise<TripSummary> {
  return apiRequest<TripSummary>("/api/trips", {
    method: "POST",
    body: JSON.stringify(trip),
  });
}

export function loadParticipantTrip(tripId: string): Promise<TripDetail> {
  return apiRequest<TripDetail>(`/api/trips/${encodeURIComponent(tripId)}`);
}

export function loadPublicGuide(publicToken: string): Promise<GuideDetail> {
  return apiRequest<GuideDetail>(
    `/api/public-guides/${encodeURIComponent(publicToken)}`,
  );
}

export function loadPublication(tripId: string): Promise<PublicationState> {
  return apiRequest<PublicationState>(
    `/api/trips/${encodeURIComponent(tripId)}/publication`,
  );
}

export function publishTrip(
  tripId: string,
  startingRevision: number,
): Promise<PublicationState> {
  return apiRequest<PublicationState>(
    `/api/trips/${encodeURIComponent(tripId)}/publication`,
    {
      method: "POST",
      body: JSON.stringify({ starting_revision: startingRevision }),
    },
  );
}

export function unpublishTrip(
  tripId: string,
  startingRevision: number,
): Promise<PublicationState> {
  return apiRequest<PublicationState>(
    `/api/trips/${encodeURIComponent(tripId)}/publication`,
    {
      method: "DELETE",
      body: JSON.stringify({ starting_revision: startingRevision }),
    },
  );
}

export function rotatePublicLink(
  tripId: string,
  startingRevision: number,
): Promise<PublicationState> {
  return apiRequest<PublicationState>(
    `/api/trips/${encodeURIComponent(tripId)}/publication/rotate`,
    {
      method: "POST",
      body: JSON.stringify({ starting_revision: startingRevision }),
    },
  );
}

export function updateTripDetails(
  tripId: string,
  details: TripDetailsUpdate,
): Promise<TripDetail> {
  return apiRequest<TripDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/details`,
    { method: "PUT", body: JSON.stringify(details) },
  );
}

export function writeDailyPlan(
  tripId: string, date: string, plan: DailyPlanWrite,
): Promise<DailyPlanResponse> {
  return apiRequest<DailyPlanResponse>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(date)}`,
    { method: "PUT", body: JSON.stringify(plan) },
  );
}

export function clearDailyPlan(
  tripId: string, date: string, startingRevision: number,
): Promise<void> {
  return apiRequest<void>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(date)}`,
    { method: "DELETE", body: JSON.stringify({ starting_revision: startingRevision }) },
  );
}

export function moveDailyPlan(
  tripId: string, planId: string, targetDate: string, startingRevision: number,
): Promise<DailyPlanResponse> {
  return apiRequest<DailyPlanResponse>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(planId)}/move`,
    { method: "POST", body: JSON.stringify({ starting_revision: startingRevision, target_date: targetDate }) },
  );
}

export function writeStay(
  tripId: string,
  planId: string,
  stay: StayWrite,
): Promise<StayDetail> {
  return apiRequest<StayDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(planId)}/stay`,
    { method: "PUT", body: JSON.stringify(stay) },
  );
}

export function clearStay(
  tripId: string,
  planId: string,
  startingRevision: number,
): Promise<void> {
  return apiRequest<void>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(planId)}/stay`,
    {
      method: "DELETE",
      body: JSON.stringify({ starting_revision: startingRevision }),
    },
  );
}

export function createTimelineEntry(
  tripId: string,
  planId: string,
  startingRevision: number,
  entry: TimelineEntryWrite,
): Promise<TripDetail> {
  return apiRequest<TripDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(planId)}/timeline`,
    { method: "POST", body: JSON.stringify({ ...entry, starting_revision: startingRevision }) },
  );
}

export function updateTimelineEntry(
  tripId: string,
  planId: string,
  entryId: string,
  startingRevision: number,
  entry: TimelineEntryWrite,
): Promise<TripDetail> {
  return apiRequest<TripDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(planId)}/timeline/${encodeURIComponent(entryId)}`,
    { method: "PUT", body: JSON.stringify({ ...entry, starting_revision: startingRevision }) },
  );
}

export function deleteTimelineEntry(
  tripId: string,
  planId: string,
  entryId: string,
  startingRevision: number,
  startingCollectionRevision: number,
): Promise<TripDetail> {
  return apiRequest<TripDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(planId)}/timeline/${encodeURIComponent(entryId)}`,
    {
      method: "DELETE",
      body: JSON.stringify({
        starting_revision: startingRevision,
        starting_collection_revision: startingCollectionRevision,
      }),
    },
  );
}

export function reorderTimelineEntries(
  tripId: string,
  planId: string,
  startingRevision: number,
  entryIds: string[],
): Promise<TripDetail> {
  return apiRequest<TripDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(planId)}/timeline/reorder`,
    {
      method: "POST",
      body: JSON.stringify({ starting_revision: startingRevision, entry_ids: entryIds }),
    },
  );
}

export function moveTimelineEntry(
  tripId: string,
  sourcePlanId: string,
  entryId: string,
  sourceStartingRevision: number,
  targetPlanId: string,
  targetStartingRevision: number,
): Promise<TripDetail> {
  return apiRequest<TripDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(sourcePlanId)}/timeline/${encodeURIComponent(entryId)}/move`,
    {
      method: "POST",
      body: JSON.stringify({
        source_starting_revision: sourceStartingRevision,
        target_plan_id: targetPlanId,
        target_starting_revision: targetStartingRevision,
      }),
    },
  );
}

export function createPhoto(
  tripId: string,
  planId: string,
  startingRevision: number,
  url: string,
  caption: string,
): Promise<TripDetail> {
  return apiRequest<TripDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(planId)}/photos`,
    {
      method: "POST",
      body: JSON.stringify({ starting_revision: startingRevision, url, caption }),
    },
  );
}

export function deletePhoto(
  tripId: string,
  planId: string,
  photoId: string,
  startingRevision: number,
): Promise<TripDetail> {
  return apiRequest<TripDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(planId)}/photos/${encodeURIComponent(photoId)}`,
    {
      method: "DELETE",
      body: JSON.stringify({ starting_revision: startingRevision }),
    },
  );
}

export function reorderPhotos(
  tripId: string,
  planId: string,
  startingRevision: number,
  photoIds: string[],
): Promise<TripDetail> {
  return apiRequest<TripDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(planId)}/photos/reorder`,
    {
      method: "POST",
      body: JSON.stringify({
        starting_revision: startingRevision,
        photo_ids: photoIds,
      }),
    },
  );
}
import { sessionCsrfToken } from "./auth";
