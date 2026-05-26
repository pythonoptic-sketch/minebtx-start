# Website

This repository now includes a static landing page inspired by the public
minebtx site.

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

The page is static and can be deployed to GitHub Pages, Netlify, Vercel, Caddy,
Nginx, or any other static host. When served from a `minebtx.com` hostname, the
stat cards fetch `/stats`. Local previews and unrelated hostnames keep the
bundled snapshot values visible to avoid cross-origin errors from the public
stats endpoint.
