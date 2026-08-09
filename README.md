# Lucknow Deal Command Center — free auto-updater

This little repo is a **free robot** that refreshes your app's data every day, on its own.
No server, no cost, nothing to run by hand.

## What's inside
- `data.json` — the data your app reads (seed deals + live demand signals).
- `scripts/update.py` — pulls fresh Lucknow commercial-demand signals from Google News RSS (free, no API key). Standard-library Python only.
- `.github/workflows/update.yml` — a GitHub Action that runs `update.py` **every day** and commits the new `data.json`.

## Set it up once (5 minutes) — see the Setup PDF for screenshots
1. Create a free **GitHub** account.
2. Create a new **public** repository (e.g. `lucknow-data`).
3. Upload these files (keep the folder structure): `data.json`, `scripts/update.py`, `.github/workflows/update.yml`, this `README.md`.
4. Open the **Actions** tab → enable workflows → run **Update Lucknow data** once (optional, to fill it now).
5. Your data URL is:
   `https://cdn.jsdelivr.net/gh/YOUR-USERNAME/lucknow-data@main/data.json`
6. In the app → **Setup → Auto-feed** → paste that URL → **Save & Sync**.

That's it. The Action runs daily for free and the app shows the fresh data — you never touch it again.

## Make it yours
- Add or change sources: edit the `QUERIES` list in `scripts/update.py`.
- Change how signals are scored: edit the numbers in the `parse()` function.
- Want deals (auctions/RERA/listings) too? Add a fetcher for those sources in `update.py` and append their records — same format as the seed deals.

## Why this and not a paid database
It's free forever (public repos get unlimited GitHub Actions), it updates itself on a schedule, and your data lives in a plain file you own. Prefer a real database later? The same app also reads any JSON API — Supabase or Cloudflare both have free tiers.
