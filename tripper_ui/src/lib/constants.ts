export const API = {
  OPEN_METEO_FORECAST: 'https://api.open-meteo.com/v1/forecast',
  OPEN_METEO_ARCHIVE: 'https://archive-api.open-meteo.com/v1/archive',
  DAYS_JSON: `${import.meta.env.BASE_URL}data/days.json`,
  TRIP_JSON: `${import.meta.env.BASE_URL}data/trip.json`,
} as const;
