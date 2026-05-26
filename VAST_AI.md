# Vast.ai GPU Rentals

BTX Start shows a same-origin `vast-offers.json` snapshot built from the
Vast.ai Search Offers API. This keeps the public page fast and avoids exposing a
private Vast API key in browser JavaScript.

## Referral Configuration

Set the actual referral URL in `vast-referral.json`:

```json
{
  "referral_configured": true,
  "referral_url": "https://cloud.vast.ai/?ref=YOUR_REAL_REFERRAL_ID"
}
```

Use the exact referral URL copied from Vast account settings. Vast also supports
public template referral links; if you create a BTX Start template, paste that
template referral URL here instead.

The site displays a disclosure next to the rental table. Referral earnings are
separate from the BTX mining fee policy. BTX Start platform fee remains 0.00%.

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
