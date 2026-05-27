# Website

This repository now includes the BTX Start static landing page. The page is
intended to be a competitive onboarding frontend, not a redirect back to the
reference site.

## Local preview

From the repository root:

```bash
python3 -m http.server 8080
```

Then open:

```text
http://localhost:8080/
```

## Files

- `index.html` - page structure and links
- `assets/styles.css` - responsive layout and visual design
- `assets/site.js` - live stat hydration, copy button behavior, and hero canvas
- `assets/og-image.png` - search/social preview image
- `assets/favicon.svg` - browser icon
- `assets/apple-touch-icon.png` - mobile home-screen icon
- `robots.txt` and `sitemap.xml` - crawler discovery files
- `llms.txt` - concise AI/search assistant context
- `START_IMPROVEMENTS.md` - release-based onboarding analysis
- `TREASURY.md` - platform fee wallet and backend policy procedure
- `WALLET_SETUP.md` - miner-facing setup guide
- `platform-treasury.json` - public platform treasury status and address data
- `stats-snapshot.json` - same-origin stats payload for the static page

The page is static and can be deployed to GitHub Pages, Netlify, Vercel, Caddy,
Nginx, or any other static host. It reads `stats-snapshot.json` from the same
site origin. The GitHub Action in `.github/workflows/update-stats.yml` refreshes
that snapshot from the current BTX backend until an independent BTX Start stats
backend has been deployed.
