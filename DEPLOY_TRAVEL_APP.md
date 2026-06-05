# Evarian travel app deployment

The public app is now the root `index.html` on `drinknile.com`.

## Fast public hosting

The domain already has `CNAME` set to:

```text
drinknile.com
```

Push `main` to the `pages` remote:

```bash
git push pages main
```

GitHub Pages will serve the static app. The waitlist form stores locally until
the `/api/waitlist` backend is deployed.

## Full-control server hosting

Point these DNS records to the Hetzner server IP:

| Type | Name | Value |
|---|---|---|
| A | `@` | server IPv4 |
| A | `www` | server IPv4 |
| A | `api` | server IPv4 |

On the server, run:

```bash
sudo deploy/scripts/bootstrap-travel-app.sh
```

This installs:

- Caddy serving `drinknile.com` from `/opt/evarian`
- `evarian-api.service` running `backend.travel_app:app`
- SQLite waitlist and trip-order storage in `/var/lib/evarian/evarian.sqlite3`

Check:

```bash
curl -fsS https://drinknile.com/
curl -fsS https://drinknile.com/api/health
curl -fsS https://api.drinknile.com/api/health
```

## Product structure

The app is organized around a Universal Trip Order:

- traveler intent
- flight product, PNR, ticket coupon, fare rules
- paid ancillaries such as seats and bags
- hotel and transfer records
- wallet authority and approval caps
- monitoring for delay, waiver, weather, traffic, and hotel risk
- allowed actions such as hold, modify, cancel, refund, rebook, and escalate
