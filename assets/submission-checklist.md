# Hey Bible Podcast — Submission Checklist

## ✅ Pre-Submission Requirements

### Technical Requirements

| Requirement | Status | Notes |
|-------------|--------|-------|
| RSS Feed URL | ⬜ | Required by all platforms |
| Cover Art (1400x1400 - 3000x3000) | ✅ | `podcast-cover.png` |
| MP3 Audio Files | ⬜ | 128+ kbps recommended |
| At least 1 episode published | ⬜ | Some platforms require 3+ |
| Valid email address | ⬜ | For verification |

---

## 🍎 Apple Podcasts Connect

**Portal:** [podcastsconnect.apple.com](https://podcastsconnect.apple.com)

### Requirements

| Requirement | Specification |
|-------------|---------------|
| **Cover Art** | 1400×1400 to 3000×3000 pixels, JPG or PNG, RGB color space |
| **RSS Feed** | Valid RSS 2.0 with `<enclosure>` tags |
| **Category** | Primary: Religion & Spirituality |
| **Explicit** | Mark as "Clean" |
| **Language** | English |

### Apple-Specific Metadata

- **Show Name:** Hey Bible Podcast
- **Author:** Working Dev's Hero LLC (or host name)
- **Description:** Use Option A from marketing-copy.md
- **Website:** https://podcast.heybible.org (brand alias: https://✝️.fm)
- **Copyright:** © 2026 Working Dev's Hero LLC

### Submission Steps

1. Log into [Apple Podcasts Connect](https://podcastsconnect.apple.com)
2. Click "Add" (+) button
3. Enter RSS feed URL
4. Review auto-populated metadata
5. Upload cover art (if not in RSS)
6. Select categories
7. Submit for review

**Review Time:** 24-72 hours typically

---

## 🎵 Spotify for Podcasters

**Portal:** [podcasters.spotify.com](https://podcasters.spotify.com)

### Requirements

| Requirement | Specification |
|-------------|---------------|
| **Cover Art** | Square, 640×640 minimum (larger is better) |
| **RSS Feed** | Must include at least 1 episode |
| **Email** | Must own/verify email in RSS feed |

### Spotify-Specific Metadata

- **Podcast Name:** Hey Bible Podcast
- **Description:** Short description (use 120-char version)
- **Language:** English
- **Category:** Religion & Spirituality

### Submission Steps

1. Go to [Spotify for Podcasters](https://podcasters.spotify.com)
2. Click "Add or claim your podcast"
3. Enter RSS feed URL
4. Verify ownership (email link sent to RSS email)
5. Add podcast details
6. Submit

**Review Time:** Usually within a few hours

---

## 🔍 Google Podcasts

**Note:** Google Podcasts has been deprecated. Podcasts now appear through **Google Search** and **YouTube Music**.

### Google Search Discovery

- Ensure RSS feed is publicly accessible
- Submit sitemap to Google Search Console
- Use structured data markup on website

### YouTube Music Podcasts

**Portal:** [support.google.com/youtubemusic](https://support.google.com/youtubemusic)

- YouTube Music now supports RSS-based podcasts
- Requires YouTube channel in good standing
- Apply through [this form](https://support.google.com/youtubemusic/answer/14199862)

---

## 📻 Additional Platforms

### Overcast

- Automatically indexes all public podcasts
- No submission required
- Ensure RSS feed is valid

### Pocket Casts

**Portal:** [pocketcasts.com/submit](https://pocketcasts.com/submit/)

- Submit RSS feed URL
- Usually approved within 24 hours

### Stitcher

**Portal:** [partnerhelp.stitcher.com](https://partnerhelp.stitcher.com/)

- Requires account creation
- Submit via partner portal

### iHeartRadio

**Portal:** [podcasters.iheart.com](https://podcasters.iheart.com/)

- Sign up for Podcasters portal
- Submit RSS feed

### TuneIn

**Portal:** [help.tunein.com](https://help.tunein.com/)

- Email request to add podcast
- Include RSS feed URL and description

### Amazon Music / Audible

**Portal:** [music.amazon.com/podcasts](https://music.amazon.com/podcasts)

- Submit via Amazon Music for Creators
- Growing platform worth considering

---

## 📋 RSS Feed Checklist

Ensure your RSS feed includes:

```xml
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
  <channel>
    <title>Hey Bible Podcast</title>
    <link>https://podcast.heybible.org</link>
    <language>en</language>
    <itunes:author>Working Dev's Hero LLC</itunes:author>
    <itunes:category text="Religion &amp; Spirituality">
      <itunes:category text="Christianity"/>
    </itunes:category>
    <itunes:image href="https://podcast.heybible.org/podcast-cover.png"/>
    <itunes:explicit>clean</itunes:explicit>
    <description>The Bible as a podcast. One book each month.</description>
    <!-- Episodes -->
    <item>
      <title>Genesis Chapter 1</title>
      <enclosure url="..." length="..." type="audio/mpeg"/>
      <itunes:duration>00:04:30</itunes:duration>
      <pubDate>...</pubDate>
    </item>
  </channel>
</rss>
```

---

## 🚀 Launch Timeline Recommendation

| Day | Task |
|-----|------|
| Day 1 | Submit to Apple Podcasts (longest review time) |
| Day 1 | Submit to Spotify |
| Day 2 | Submit to Pocket Casts, Stitcher |
| Day 3 | Submit to Amazon Music |
| Day 5 | Verify Apple approval |
| Day 7 | Announce launch on social media |

---

## 🔗 Quick Links

- **Apple Podcasts Connect:** https://podcastsconnect.apple.com
- **Spotify for Podcasters:** https://podcasters.spotify.com
- **Pocket Casts Submit:** https://pocketcasts.com/submit/
- **YouTube Music Podcasts:** https://support.google.com/youtubemusic/answer/14199862

---

## 📊 Post-Submission Tracking

Create accounts to track analytics:

- [ ] Apple Podcasts Connect (analytics dashboard)
- [ ] Spotify for Podcasters (analytics dashboard)
- [ ] Podtrac (free stats service)
- [ ] Chartable (ranking tracking)
