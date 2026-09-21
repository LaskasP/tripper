export interface Location {
  lat: number;
  lng: number;
}

export interface TripConfig {
  name: string;
  destination: string;
  short_name: string;
  description: string;
  timezone: string;
  location: Location;
  start_date: string;
  end_date: string;
}

export interface TimelineEntry {
  time: string;
  title: string;
  description: string;
  location?: Location;
  locationName?: string;
}

export type BookingPlatform = "booking.com" | "airbnb";

export interface Stay {
  name: string;
  address: string;
  location: Location;
  checkIn?: string;
  checkOut?: string;
  bookingUrl?: string;
  platform?: BookingPlatform;
}

export interface PhotoItem {
  url: string;
  caption: string;
}

export interface Weather {
  icon: string;
  high: number;
  low: number;
  description: string;
}

export interface Day {
  date: string;
  dayNumber: number;
  title: string;
  summary: string;
  backgroundImage: string;
  weather?: Weather;
  stay: Stay;
  timeline: TimelineEntry[];
  photos: PhotoItem[];
}
