# BTX Start Backend DNS

The public website uses GitHub Pages:

```text
drinknile.com
www.drinknile.com
```

Do not point backend traffic at GitHub Pages. The mining backend needs separate
records:

## Required Backend Records

Add these after the backend VM or provider gives you a stable target:

```text
stratum.drinknile.com  A      <BACKEND_VM_IPV4>
api.drinknile.com      A      <BACKEND_VM_IPV4>
```

If the provider gives a hostname instead of a static IP:

```text
api.drinknile.com      CNAME  <BACKEND_API_HOSTNAME>
```

Use an `A` record for `stratum.drinknile.com` whenever possible. TCP stratum
traffic must go directly to the pool server on port `3333`.

## Ports

```text
3333/tcp  stratum server
443/tcp   HTTPS stats API and dashboard API
80/tcp    ACME HTTP challenge or HTTP-to-HTTPS redirect
```

## Cloudflare / Proxy Warning

If DNS is later moved through Cloudflare, keep `stratum.drinknile.com` DNS-only.
Standard Cloudflare HTTP proxying does not proxy raw stratum TCP on port 3333.

## Cutover Verification

After DNS is live:

```sh
STATS_URL='https://api.drinknile.com/stats' \
STRATUM_HOST='stratum.drinknile.com' \
STRATUM_PORT='3333' \
EXPECTED_POOL_FEE_BPS='0' \
PROTECTED_PAYOUT_ADDRESSES='btx1z...personal...,btx1z...vast...' \
scripts/verify-owned-backend.sh
```

Do not announce mining as live until that script passes.
