import type { APIRoute } from 'astro';
import { availableBooks, bookAudioUrl, bookChaptersJsonUrl } from '~/lib/books';
import { fetchChapters } from '~/lib/chapters';

const SITE = 'https://xn--pci.fm';
const TITLE = 'The Hey Bible Podcast';
const DESCRIPTION =
  'The whole Bible read aloud, one book at a time. A new book every month. World English Bible — public domain (https://worldenglish.bible).';
const AUTHOR = "Working Dev's Hero";
const EMAIL = 'bobby@heybible.org';
const IMAGE = `${SITE}/og-image.png`;

function escapeXml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return [h, m, s].map((n) => n.toString().padStart(2, '0')).join(':');
}

export const GET: APIRoute = async () => {
  const books = availableBooks();
  const now = new Date().toUTCString();

  const items = await Promise.all(
    books.map(async (book, idx) => {
      const audioUrl = bookAudioUrl(book);
      const chaptersUrl = bookChaptersJsonUrl(book);
      const manifest = await fetchChapters(book);
      const sizeBytes = book.releaseSize ?? 0;
      const duration = manifest?.duration ?? 0;

      // Stagger pubDates so podcast clients order books canonically
      const pubDate = new Date(Date.now() - (books.length - idx) * 86400000).toUTCString();

      return `
    <item>
      <title>${escapeXml(`The Book of ${book.name}`)}</title>
      <description>${escapeXml(`The complete book of ${book.name} from the World English Bible.`)}</description>
      <link>${SITE}/books/${book.slug}/</link>
      <guid isPermaLink="false">heybible-fm-${book.slug}</guid>
      <pubDate>${pubDate}</pubDate>
      <enclosure url="${audioUrl}" length="${sizeBytes}" type="audio/mpeg" />
      <itunes:author>${escapeXml(AUTHOR)}</itunes:author>
      <itunes:duration>${formatDuration(duration)}</itunes:duration>
      <itunes:episode>${idx + 1}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
      <podcast:chapters url="${chaptersUrl}" type="application/json+chapters" />
    </item>`;
    })
  );

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:podcast="https://podcastindex.org/namespace/1.0"
  xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${escapeXml(TITLE)}</title>
    <link>${SITE}/</link>
    <atom:link href="${SITE}/feed.xml" rel="self" type="application/rss+xml" />
    <description>${escapeXml(DESCRIPTION)}</description>
    <language>en-us</language>
    <copyright>Public domain — World English Bible (https://worldenglish.bible)</copyright>
    <lastBuildDate>${now}</lastBuildDate>
    <itunes:author>${escapeXml(AUTHOR)}</itunes:author>
    <itunes:summary>${escapeXml(DESCRIPTION)}</itunes:summary>
    <itunes:owner>
      <itunes:name>${escapeXml(AUTHOR)}</itunes:name>
      <itunes:email>${escapeXml(EMAIL)}</itunes:email>
    </itunes:owner>
    <itunes:image href="${IMAGE}" />
    <itunes:category text="Religion &amp; Spirituality">
      <itunes:category text="Christianity" />
    </itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>serial</itunes:type>${items.join('')}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/rss+xml; charset=utf-8',
    },
  });
};
