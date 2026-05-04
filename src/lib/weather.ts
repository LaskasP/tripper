import type { Weather } from '../types';
import { API } from './constants';

const WMO_ICONS: Record<number, { icon: string; description: string }> = {
  0: { icon: '☀️', description: 'Clear sky' },
  1: { icon: '🌤️', description: 'Mainly clear' },
  2: { icon: '⛅', description: 'Partly cloudy' },
  3: { icon: '☁️', description: 'Overcast' },
  45: { icon: '🌫️', description: 'Fog' },
  48: { icon: '🌫️', description: 'Depositing rime fog' },
  51: { icon: '🌦️', description: 'Light drizzle' },
  53: { icon: '🌦️', description: 'Moderate drizzle' },
  55: { icon: '🌧️', description: 'Dense drizzle' },
  61: { icon: '🌧️', description: 'Slight rain' },
  63: { icon: '🌧️', description: 'Moderate rain' },
  65: { icon: '🌧️', description: 'Heavy rain' },
  71: { icon: '🌨️', description: 'Slight snow' },
  73: { icon: '🌨️', description: 'Moderate snow' },
  75: { icon: '❄️', description: 'Heavy snow' },
  80: { icon: '🌦️', description: 'Slight showers' },
  81: { icon: '🌧️', description: 'Moderate showers' },
  82: { icon: '⛈️', description: 'Violent showers' },
  95: { icon: '⛈️', description: 'Thunderstorm' },
  96: { icon: '⛈️', description: 'Thunderstorm with hail' },
  99: { icon: '⛈️', description: 'Thunderstorm with heavy hail' },
};

function wmoToWeather(code: number, high: number, low: number): Weather {
  const entry = WMO_ICONS[code] ?? { icon: '🌡️', description: 'Unknown' };
  return {
    icon: entry.icon,
    high: Math.round(high),
    low: Math.round(low),
    description: entry.description,
  };
}

interface OpenMeteoDaily {
  time: string[];
  temperature_2m_max: number[];
  temperature_2m_min: number[];
  weather_code: number[];
}

interface OpenMeteoResponse {
  daily: OpenMeteoDaily;
}

/**
 * Fetch weather for a date range from Open-Meteo.
 * Uses the forecast API if dates are near, otherwise
 * falls back to the historical archive API with the
 * same dates from the previous year.
 */
export async function fetchWeather(
  lat: number,
  lng: number,
  startDate: string,
  endDate: string,
  timezone: string,
): Promise<Map<string, Weather>> {
  const result = new Map<string, Weather>();

  const now = new Date();
  const start = new Date(startDate + 'T00:00:00');
  const daysUntilStart = (start.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);

  let data: OpenMeteoResponse | null = null;
  let dateMapping: Map<string, string> | null = null;

  // Try forecast API if dates are within ~14 days
  if (daysUntilStart <= 14) {
    data = await tryFetch(
      `${API.OPEN_METEO_FORECAST}?latitude=${lat}&longitude=${lng}&daily=temperature_2m_max,temperature_2m_min,weather_code&temperature_unit=celsius&start_date=${startDate}&end_date=${endDate}&timezone=${encodeURIComponent(timezone)}`,
    );
  }

  // Fall back to historical API using previous year's dates
  if (!data) {
    const prevStart = shiftYear(startDate, -1);
    const prevEnd = shiftYear(endDate, -1);
    dateMapping = new Map<string, string>();
    // Map historical dates back to trip dates
    let d = new Date(startDate + 'T00:00:00');
    let h = new Date(prevStart + 'T00:00:00');
    while (d <= new Date(endDate + 'T00:00:00')) {
      dateMapping.set(toISODate(h), toISODate(d));
      d.setDate(d.getDate() + 1);
      h.setDate(h.getDate() + 1);
    }

    data = await tryFetch(
      `${API.OPEN_METEO_ARCHIVE}?latitude=${lat}&longitude=${lng}&daily=temperature_2m_max,temperature_2m_min,weather_code&temperature_unit=celsius&start_date=${prevStart}&end_date=${prevEnd}&timezone=${encodeURIComponent(timezone)}`,
    );
  }

  if (!data?.daily) return result;

  const { time, temperature_2m_max, temperature_2m_min, weather_code } = data.daily;

  for (let i = 0; i < time.length; i++) {
    const tripDate = dateMapping ? (dateMapping.get(time[i]) ?? time[i]) : time[i];
    result.set(
      tripDate,
      wmoToWeather(weather_code[i], temperature_2m_max[i], temperature_2m_min[i]),
    );
  }

  return result;
}

async function tryFetch(url: string): Promise<OpenMeteoResponse | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function shiftYear(dateStr: string, offset: number): string {
  const [y, m, d] = dateStr.split('-');
  return `${Number(y) + offset}-${m}-${d}`;
}

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}
