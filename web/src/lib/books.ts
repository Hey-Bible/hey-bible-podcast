import booksData from '~/data/books.json';

export type BookStatus = 'available' | 'in-progress' | 'coming-soon';
export type Testament = 'old' | 'new';

export interface BookProgress {
  chapter: number;
  verse: number;
  completedVerses: number;
}

export interface Book {
  slug: string;
  name: string;
  testament: Testament;
  chapters: number;
  totalVerses: number;
  status: BookStatus;
  releaseTag: string | null;
  releaseSize: number | null;
  progress?: BookProgress;
}

// Public base URL for the R2 bucket that hosts {book}-web.mp3 and
// {book}-web.json. Must be served with Content-Type: audio/mpeg and
// Content-Disposition: inline so iOS Safari will stream instead of trying to
// download — see scripts/release-book.py for the upload-side headers.
//
// TODO: replace once the R2 bucket + custom domain are live (e.g.
// "https://audio.heybible.org"). Until then, audio playback is broken.
export const R2_PUBLIC_BASE = 'https://audio.heybible.org';

export const books = booksData as Book[];

export function getBook(slug: string): Book | undefined {
  return books.find((b) => b.slug === slug);
}

export function availableBooks(): Book[] {
  return books.filter((b) => b.status === 'available');
}

export function inProgressBook(): Book | undefined {
  return books.find((b) => b.status === 'in-progress');
}

export function latestRelease(): Book | undefined {
  const avail = availableBooks();
  return avail[avail.length - 1];
}

export function oldTestament(): Book[] {
  return books.filter((b) => b.testament === 'old');
}

export function newTestament(): Book[] {
  return books.filter((b) => b.testament === 'new');
}

export function bookAudioUrl(book: Book): string {
  return `${R2_PUBLIC_BASE}/${book.slug}-web.mp3`;
}

export function bookChaptersJsonUrl(book: Book): string {
  return `${R2_PUBLIC_BASE}/${book.slug}-web.json`;
}
