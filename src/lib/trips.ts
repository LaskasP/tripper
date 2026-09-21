export type TripRole = 'creator' | 'contributor' | 'traveller';

export interface TripSummary {
  id: string;
  name: string;
  destination: string;
  shortName: string;
  startDate: string;
  endDate: string;
  role: TripRole;
}

export interface NewTrip {
  name: string;
  destination: string;
  shortName: string;
  description: string;
  timezone: string;
  location: { lat: number; lng: number };
  startDate: string;
  endDate: string;
}

export interface PublicTrip extends NewTrip {
  id: string;
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(response.status === 401 ? 'Sign in to manage your trips.' : 'Something went wrong. Please try again.');
  }

  return await response.json() as T;
}

export function loadMyTrips(): Promise<TripSummary[]> {
  return apiRequest<TripSummary[]>('/api/me/trips');
}

export function createTrip(trip: NewTrip): Promise<TripSummary> {
  return apiRequest<TripSummary>('/api/trips', {
    method: 'POST',
    body: JSON.stringify(trip),
  });
}

export function loadPublicTrip(tripId: string): Promise<PublicTrip> {
  return apiRequest<PublicTrip>(`/api/trips/${encodeURIComponent(tripId)}`);
}
