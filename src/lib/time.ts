import type { Day } from '../types';

export function todayInTimezone(timezone: string): string {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  return formatter.format(new Date());
}

export function findTodayIndex(days: Day[], timezone: string): number {
  const today = todayInTimezone(timezone);
  return days.findIndex((d) => d.date === today);
}
