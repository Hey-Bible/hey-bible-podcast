import type { Book } from './books';
import { bookChaptersJsonUrl } from './books';

export interface Chapter {
  number: number;
  title: string;
  start: number;
  end: number;
  duration: number;
}

export interface ChaptersManifest {
  book: string;
  title: string;
  duration: number;
  chapters: Chapter[];
}

const cache = new Map<string, ChaptersManifest | null>();

export async function fetchChapters(book: Book): Promise<ChaptersManifest | null> {
  if (book.status !== 'available') return null;
  const url = bookChaptersJsonUrl(book);
  if (cache.has(url)) return cache.get(url) ?? null;

  try {
    const res = await fetch(url);
    if (!res.ok) {
      console.warn(`[chapters] ${book.slug}: HTTP ${res.status} for ${url}`);
      cache.set(url, null);
      return null;
    }
    const data = (await res.json()) as ChaptersManifest;
    cache.set(url, data);
    return data;
  } catch (err) {
    console.warn(`[chapters] ${book.slug}: fetch failed —`, err);
    cache.set(url, null);
    return null;
  }
}

export function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds)) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
