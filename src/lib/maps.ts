import type { Location } from '../types';

export function googleMapsUrl(location: Location): string;
export function googleMapsUrl(address: string): string;
export function googleMapsUrl(input: Location | string): string {
  const query =
    typeof input === 'string'
      ? encodeURIComponent(input)
      : `${input.lat},${input.lng}`;
  return `https://www.google.com/maps/search/?api=1&query=${query}`;
}
