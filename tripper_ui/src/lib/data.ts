import type { Day, TripConfig } from '../types';
import { API } from './constants';

export async function loadTrip(): Promise<TripConfig> {
  const response = await fetch(API.TRIP_JSON);
  if (!response.ok) {
    throw new Error(`Failed to load trip config: ${response.status}`);
  }
  return await response.json();
}

export async function loadDays(): Promise<Day[]> {
  const response = await fetch(API.DAYS_JSON);
  if (!response.ok) {
    throw new Error(`Failed to load trip data: ${response.status}`);
  }
  const days: Day[] = await response.json();
  return days;
}
