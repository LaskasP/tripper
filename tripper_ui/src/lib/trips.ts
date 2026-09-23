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

export interface TripDetail {
  id: string;
  revision: number;
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
    timeline: Array<{
      time: string;
      title: string;
      description: string;
      location: { lat: number; lng: number } | null;
      location_name: string | null;
    }>;
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
import { sessionCsrfToken } from "./auth";
