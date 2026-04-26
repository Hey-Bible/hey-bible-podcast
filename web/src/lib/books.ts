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

export function releaseUrl(book: Book, asset: string): string {
  const tag = book.releaseTag ?? `${book.slug}-latest`;
  return `https://github.com/wdh-claudius/web-bible-audio/releases/download/${tag}/${asset}`;
}

export function bookAudioUrl(book: Book): string {
  return releaseUrl(book, `${book.slug}-complete.mp3`);
}

export function bookChaptersJsonUrl(book: Book): string {
  return releaseUrl(book, `${book.slug}-chapters.json`);
}
