export interface Location {
  lat: number;
  lng: number;
}

export interface TimelineEntry {
  time: string;
  title: string;
  description: string;
  location?: Location;
  location_name?: string;
}

export type BookingPlatform = "booking.com" | "airbnb";

export interface Stay {
  id?: string;
  revision?: number;
  name: string;
  address: string;
  location?: Location;
  check_in?: string;
  check_out?: string;
  public_listing_url?: string;
  booking_platform?: BookingPlatform;
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
  day_number: number;
  title: string;
  summary: string;
  background_image: string;
  weather?: Weather;
  stay?: Stay;
  timeline: TimelineEntry[];
  photos: PhotoItem[];
}
