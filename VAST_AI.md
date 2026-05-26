# Vast.ai GPU Rentals

BTX Start shows a same-origin `vast-offers.json` snapshot built from the
Vast.ai Search Offers API. This keeps the public page fast and avoids exposing a
private Vast API key in browser JavaScript.

## Referral Configuration

Set the actual referral URL in `vast-referral.json`:

```json
{
  "referral_configured": true,
  "referral_id": "556354",
  "referral_url": "https://cloud.vast.ai/?ref_id=556354"
}
```

Use the exact referral URL copied from Vast account settings. Vast also supports
public template referral links; if you create a BTX Start template, paste that
template referral URL here instead.

The site displays a disclosure next to the rental table. Referral earnings are
separate from the BTX mining fee policy. BTX Start platform fee remains 0.00%.

Do not commit a Vast API key. Store it as the GitHub Actions repository secret
`VAST_API_KEY`; the refresh workflow passes it only to
`scripts/update-vast-offers.js` while generating `vast-offers.json`.

## Pricing Refresh

Manual refresh:

```sh
node scripts/update-vast-offers.js vast-offers.json
```

Automatic refresh:

```text
.github/workflows/update-vast-offers.yml
```

The workflow refreshes twice per hour and commits `vast-offers.json` when prices
or available offers change.

## Ranking

The page ranks Vast offers by:

- hourly rental price from Vast
- matched BTX Start GPU profile
- estimated BTX/hour from the current network model
- estimated cost per BTX
- Vast reliability signal

Final rental price and availability are always confirmed on Vast.ai.
