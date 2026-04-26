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
  releaseTag: string;
  chapters: Chapter[];
}

const cache = new Map<string, ChaptersManifest | null>();

// compile-book.py emits two segments per chapter (the spoken "Chapter N" title
// clip, then the content). Collapse them so the UI shows one row per chapter
// that spans both — clicking starts at the title so listeners hear the intro.
function mergeChapterSegments(chapters: Chapter[]): Chapter[] {
  const out: Chapter[] = [];
  for (const c of chapters) {
    const prev = out[out.length - 1];
    if (prev && prev.number === c.number) {
      prev.end = c.end;
      prev.duration = prev.end - prev.start;
    } else {
      out.push({ ...c });
    }
  }
  return out;
}

export async function fetchChapters(book: Book): Promise<ChaptersManifest | null> {
  if (book.status !== 'available' || !book.releaseTag) return null;
  const url = bookChaptersJsonUrl(book);
  if (cache.has(url)) return cache.get(url) ?? null;

  try {
    const res = await fetch(url);
    if (!res.ok) {
      console.warn(`[chapters] ${book.slug}: HTTP ${res.status} for ${url}`);
      cache.set(url, null);
      return null;
    }
    const raw = (await res.json()) as ChaptersManifest;
    const data: ChaptersManifest = {
      ...raw,
      chapters: mergeChapterSegments(raw.chapters ?? []),
    };
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
