/**
 * Interactive CLI to add or edit a full Day in days.json.
 * Run: npm run edit-day
 *
 * Features:
 *   - Add a brand-new day or edit an existing one by date
 *   - Prompts for every field: title, summary, background, stay, timeline, photos
 *   - Auto-geocodes addresses via the free Nominatim API (OpenStreetMap)
 *   - Writes directly to public/data/days.json (auto-sorts by date, renumbers)
 */

import * as readline from 'node:readline';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

/* ------------------------------------------------------------------ */
/*  Types (mirrored from src/types.ts to keep the script standalone)  */
/* ------------------------------------------------------------------ */

interface Location { lat: number; lng: number }
type BookingPlatform = 'booking.com' | 'airbnb';

interface Stay {
  name: string; address: string; location: Location;
  checkIn?: string; checkOut?: string;
  bookingUrl?: string; platform?: BookingPlatform;
}
interface TimelineEntry {
  time: string; title: string; description: string;
  location?: Location; locationName?: string;
}
interface PhotoItem { url: string; caption: string }

interface Day {
  date: string; dayNumber: number; title: string; summary: string;
  backgroundImage: string; stay: Stay;
  timeline: TimelineEntry[]; photos: PhotoItem[];
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

const DAYS_PATH = resolve(import.meta.dirname ?? '.', '..', 'public', 'data', 'days.json');

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
const ask = (q: string): Promise<string> =>
  new Promise((res) => rl.question(q, (a) => res(a.trim())));

interface GeoResult { lat: string; lon: string; display_name: string }

async function geocode(address: string): Promise<Location | null> {
  const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(address)}&format=json&limit=1`;
  const res = await fetch(url, { headers: { 'User-Agent': 'trip-planner-cli/1.0' } });
  if (!res.ok) return null;
  const data: GeoResult[] = await res.json();
  if (data.length === 0) return null;
  return { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) };
}

function loadDays(): Day[] {
  try {
    return JSON.parse(readFileSync(DAYS_PATH, 'utf-8'));
  } catch {
    return [];
  }
}

function saveDays(days: Day[]): void {
  days.sort((a, b) => a.date.localeCompare(b.date));
  days.forEach((d, i) => (d.dayNumber = i + 1));
  writeFileSync(DAYS_PATH, JSON.stringify(days, null, 2) + '\n');
}

/* ------------------------------------------------------------------ */
/*  Section prompts                                                   */
/* ------------------------------------------------------------------ */

async function askStay(existing?: Stay): Promise<Stay> {
  console.log('\n🏨  Stay details');
  const name     = (await ask(`  Property name${existing ? ` [${existing.name}]` : ''}: `)) || existing?.name || '';
  const address  = (await ask(`  Full address${existing ? ` [${existing.address}]` : ''}: `)) || existing?.address || '';

  console.log('  Geocoding...');
  const coords = await geocode(address) ?? existing?.location ?? { lat: 0, lng: 0 };
  if (coords.lat !== 0) console.log(`  ✅ ${coords.lat}, ${coords.lng}`);
  else console.log('  ⚠️  Could not geocode — add lat/lng manually');

  const checkIn  = (await ask(`  Check-in time [${existing?.checkIn ?? ''}]: `))  || existing?.checkIn;
  const checkOut = (await ask(`  Check-out time [${existing?.checkOut ?? ''}]: `)) || existing?.checkOut;

  const platInput = (await ask(`  Platform (booking.com / airbnb) [${existing?.platform ?? ''}]: `)) || existing?.platform || '';
  const platform: BookingPlatform | undefined =
    platInput.toLowerCase().includes('airbnb') ? 'airbnb'
    : platInput ? 'booking.com'
    : undefined;

  const bookingUrl = (await ask(`  Booking URL [${existing?.bookingUrl ?? ''}]: `)) || existing?.bookingUrl;

  const stay: Stay = { name, address, location: coords };
  if (checkIn)    stay.checkIn    = checkIn;
  if (checkOut)   stay.checkOut   = checkOut;
  if (bookingUrl) stay.bookingUrl = bookingUrl;
  if (platform)   stay.platform   = platform;
  return stay;
}

async function askSingleTimelineEntry(index: number, existing?: TimelineEntry): Promise<TimelineEntry> {
  console.log(`\n  📌 Timeline entry #${index + 1}`);
  const time  = (await ask(`    Time (HH:MM)${existing ? ` [${existing.time}]` : ''}: `)) || existing?.time || '';
  const title = (await ask(`    Title${existing ? ` [${existing.title}]` : ''}: `))       || existing?.title || '';
  const desc  = (await ask(`    Description${existing ? ` [${existing.description}]` : ''}: `)) || existing?.description || '';
  const locName = (await ask(`    Location name (optional)${existing?.locationName ? ` [${existing.locationName}]` : ''}: `)) || existing?.locationName;

  let location: Location | undefined;
  if (locName) {
    console.log('    Geocoding...');
    location = (await geocode(locName)) ?? existing?.location ?? undefined;
    if (location) console.log(`    ✅ ${location.lat}, ${location.lng}`);
  }

  const entry: TimelineEntry = { time, title, description: desc };
  if (location) entry.location = location;
  if (locName)  entry.locationName = locName;
  return entry;
}

async function askTimeline(existing: TimelineEntry[] = []): Promise<TimelineEntry[]> {
  console.log('\n📋  Timeline');
  const entries: TimelineEntry[] = [];
  let i = 0;

  // Edit existing entries
  for (const ex of existing) {
    const keep = (await ask(`  Keep entry "${ex.time} ${ex.title}"? (y/n/edit) [y]: `)) || 'y';
    if (keep.startsWith('n')) continue;
    if (keep.startsWith('e')) {
      entries.push(await askSingleTimelineEntry(i, ex));
    } else {
      entries.push(ex);
    }
    i++;
  }

  // Add new entries
  while (true) {
    const more = await ask('\n  Add another timeline entry? (y/n) [n]: ');
    if (!more.startsWith('y')) break;
    entries.push(await askSingleTimelineEntry(i));
    i++;
  }

  return entries;
}

async function askPhotos(existing: PhotoItem[] = []): Promise<PhotoItem[]> {
  console.log('\n📸  Photos');
  const photos: PhotoItem[] = [];

  for (const ex of existing) {
    const keep = (await ask(`  Keep photo "${ex.caption}"? (y/n) [y]: `)) || 'y';
    if (!keep.startsWith('n')) photos.push(ex);
  }

  while (true) {
    const more = await ask('\n  Add a photo? (y/n) [n]: ');
    if (!more.startsWith('y')) break;
    const url     = await ask('    Image URL or local path: ');
    const caption = await ask('    Caption: ');
    if (url) photos.push({ url, caption });
  }

  return photos;
}

/* ------------------------------------------------------------------ */
/*  Main                                                              */
/* ------------------------------------------------------------------ */

async function main() {
  console.log('\n✈️  Trip Day Editor\n');

  const days = loadDays();
  const dateInput = await ask('Date (YYYY-MM-DD): ');

  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateInput)) {
    console.log('❌ Invalid date format. Use YYYY-MM-DD.');
    rl.close();
    return;
  }

  const existingIdx = days.findIndex((d) => d.date === dateInput);
  const existing: Day | undefined = existingIdx >= 0 ? days[existingIdx] : undefined;

  if (existing) {
    console.log(`\n📝 Editing Day ${existing.dayNumber}: "${existing.title}" (${existing.date})`);
  } else {
    console.log(`\n🆕 Adding new day: ${dateInput}`);
  }

  const title   = (await ask(`Title${existing ? ` [${existing.title}]` : ''}: `))   || existing?.title || '';
  const summary = (await ask(`Summary${existing ? ` [${existing.summary}]` : ''}: `)) || existing?.summary || '';
  const bgImage = (await ask(`Background image URL${existing ? ` [${existing.backgroundImage}]` : ''}: `)) || existing?.backgroundImage || '';

  const stay     = await askStay(existing?.stay);
  const timeline = await askTimeline(existing?.timeline);
  const photos   = await askPhotos(existing?.photos);

  const day: Day = {
    date: dateInput,
    dayNumber: 0, // will be set by saveDays
    title,
    summary,
    backgroundImage: bgImage,
    stay,
    timeline,
    photos,
  };

  if (existingIdx >= 0) {
    days[existingIdx] = day;
  } else {
    days.push(day);
  }

  saveDays(days);
  console.log(`\n✅ Saved! days.json now has ${days.length} days.\n`);
  rl.close();
}

main();
