import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const publicDir = join(fileURLToPath(new URL('.', import.meta.url)), '../../public');

export function episodeArtSrc(slug: string): string | null {
  const file = join(publicDir, 'book-art', `${slug}.jpg`);
  return existsSync(file) ? `/book-art/${slug}.jpg` : null;
}

export function episodeArtThumbSrc(slug: string): string | null {
  const thumb = join(publicDir, 'book-art', `${slug}-thumb.jpg`);
  if (existsSync(thumb)) return `/book-art/${slug}-thumb.jpg`;
  return episodeArtSrc(slug);
}

export function episodeArtSquareHref(slug: string, site: string): string | null {
  const file = join(publicDir, 'book-art', `${slug}-square.jpg`);
  return existsSync(file) ? `${site}/book-art/${slug}-square.jpg` : null;
}
