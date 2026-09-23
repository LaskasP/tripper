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

export interface TripDetail {
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
    date: string;
    day_number: number;
    title: string;
    summary: string;
    background_image: string;
    stay: {
      name: string;
      address: string;
      location: { lat: number; lng: number } | null;
      check_in: string | null;
      check_out: string | null;
      public_listing_url: string | null;
      booking_platform: "booking.com" | "airbnb" | null;
    } | null;
    timeline: TimelineEntryDetail[];
    photos: Array<{ url: string; caption: string }>;
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

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly latest_values?: TripDetail;

  constructor(
    status: number,
    code: string,
    message: string,
    latestValues?: TripDetail,
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.latest_values = latestValues;
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
      error?: { code?: string; message?: string; latest_values?: TripDetail };
    } | null;
    throw new ApiError(
      response.status,
      body?.error?.code ?? `http_${response.status}`,
      response.status === 401
        ? "Sign in to manage your trips."
        : (body?.error?.message ?? "Something went wrong. Please try again."),
      body?.error?.latest_values,
    );
  }

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
): Promise<TripDetail> {
  return apiRequest<TripDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(date)}`,
    { method: "PUT", body: JSON.stringify(plan) },
  );
}

export function clearDailyPlan(
  tripId: string, date: string, startingRevision: number,
): Promise<TripDetail> {
  return apiRequest<TripDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(date)}`,
    { method: "DELETE", body: JSON.stringify({ starting_revision: startingRevision }) },
  );
}

export function moveDailyPlan(
  tripId: string, planId: string, targetDate: string, startingRevision: number,
): Promise<TripDetail> {
  return apiRequest<TripDetail>(
    `/api/trips/${encodeURIComponent(tripId)}/daily-plans/${encodeURIComponent(planId)}/move`,
    { method: "POST", body: JSON.stringify({ starting_revision: startingRevision, target_date: targetDate }) },
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
import { sessionCsrfToken } from "./auth";
