"""Cloudflare R2 upload helper shared by compile-book.py and release-book.py."""

import os
from pathlib import Path

# Public base URL for the bucket — must match R2_PUBLIC_BASE in
# web/src/lib/books.ts so URLs printed by these scripts are the same as the
# URLs the website builds. Site URL must match astro.config.mjs `site`.
PUBLIC_AUDIO_BASE = "https://audio.heybible.org"
SITE_URL = "https://podcast.heybible.org"

R2_CRED_KEYS = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")


def get_credentials() -> dict[str, str]:
    """Load R2 creds from environment. Raises if any are missing."""
    creds = {k: os.environ.get(k, "").strip() for k in R2_CRED_KEYS}
    missing = [k for k in R2_CRED_KEYS if not creds[k]]
    if missing:
        raise ValueError(f"Missing R2 environment variables: {', '.join(missing)}")
    return creds


def upload(mp3_path: Path, json_path: Path | None) -> bool:
    """Upload book MP3 (+ optional chapter sidecar) to R2 with audio-friendly headers.

    iOS Safari refuses to stream audio served as application/octet-stream with
    Content-Disposition: attachment, so we set both explicitly.
    """
    import boto3

    creds = get_credentials()
    bucket = creds["R2_BUCKET_NAME"]
    print(f"  Uploading to R2 (bucket: {bucket})...")

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{creds['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=creds["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=creds["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )

    if not mp3_path.exists():
        print(f"  Error: MP3 file not found: {mp3_path}")
        return False

    uploads = [(mp3_path, "audio/mpeg")]
    if json_path and json_path.exists():
        uploads.append((json_path, "application/json"))
    elif json_path:
        print(f"  Warning: Chapters JSON not found: {json_path}")

    for path, content_type in uploads:
        try:
            s3.upload_file(
                str(path),
                bucket,
                path.name,
                ExtraArgs={
                    "ContentType": content_type,
                    "ContentDisposition": "inline",
                },
            )
            print(f"  ✓ Uploaded {path.name} ({content_type})")
        except Exception as e:
            print(f"  Error uploading {path.name}: {e}")
            return False

    return True


def print_review_links(book: str, *, include_site: bool) -> None:
    """Print URLs the operator can hit to review the upload.

    `include_site=False` for compile-book.py — site doesn't surface the book
    until release-book.py flips status to available, so the page link wouldn't
    be useful yet.
    """
    print()
    print("Review links:")
    print(f"  🎧 Audio:   {PUBLIC_AUDIO_BASE}/{book}.mp3")
    print(f"  📑 Sidecar: {PUBLIC_AUDIO_BASE}/{book}-chapters.json")
    if include_site:
        print(f"  🌐 Page:    {SITE_URL}/books/{book}/")
        print(f"  📡 Feed:    {SITE_URL}/feed.xml")
