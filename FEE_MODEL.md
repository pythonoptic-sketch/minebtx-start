# BTX Pool Fee Model

Snapshot inputs, fetched May 26, 2026:

- Public page: https://drinknile.com/
- First-party stats target: https://api.drinknile.com/stats
- BTX price model: https://btxprice.com/api/current.json
- BTX forward model docs: https://btxprice.com/forward-market-price.md

## Current Observed State

BTX Start is now configured for first-party backend cutover:

- Installer default pool: `stratum.drinknile.com:3333`
- Public stats API target: `https://api.drinknile.com/stats`
- Current launch pool fee: `0 bps` = `0.00%`
- Active workers now: `0`
- Active workers, 24h: `0`
- Fee address: pending dedicated first-party backend wallet
- Treasury address: pending dedicated first-party backend wallet

From `btxprice.com/api/current.json`:

- Current BTX model price: `$5.514650`
- 12-month forward market price: `$178.164247`
- Expected 12-month multiplier: `26.8x`
- Current BTX security percent: `0.005569%`
- Expected 12-month BTX security percent: `0.149255%`

## Model

Let:

- `f` = pool fee as a decimal, for example `0.02` for `2%`
- `P_t` = BTX price at time `t`
- `B_t` = expected BTX earned by this pool before pool fee
- `epsilon` = miner price elasticity with respect to net payout
- `H(f)` = retained pool hashrate at fee `f`

Miner net payout is proportional to:

```text
net_payout(f, t) = (1 - f) * P_t
```

Pool fee revenue is:

```text
R(f, t) = f * B_t * P_t * H(f)
```

Use a constant-elasticity retention curve:

```text
H(f) = H0 * ((1 - f) / (1 - f0)) ^ epsilon
```

For pure fee-revenue maximization with all else fixed:

```text
R(f) ∝ f * (1 - f)^epsilon
d ln(R) / df = 1/f - epsilon/(1 - f)
f* = 1 / (1 + epsilon)
```

## Elasticity Table

Mining pool switching costs are low, especially before a pool has deep
reputation, TLS, dashboards, payout history, and miner tooling. That implies
high elasticity: rational miners compare net payout across pools quickly.

| Elasticity `epsilon` | Revenue-optimal fee |
| ---: | ---: |
| 20 | 4.76% |
| 30 | 3.23% |
| 40 | 2.44% |
| 50 | 1.96% |
| 60 | 1.64% |
| 80 | 1.23% |
| 100 | 0.99% |

## Price-Progression Effect

At current pool share, expected gross pool production is approximately:

```text
blocks_per_day = 86400 / 90 = 960
network_btx_per_day = 960 * 20 = 19,200 BTX
pool_btx_per_day = 19,200 * 0.0049847896499 = 95.71 BTX
```

At current model price:

```text
gross_pool_value_day = 95.71 * $5.51465 = $527.80/day
```

At 12-month forward model price, if pool share persisted:

```text
gross_pool_value_day_12m = 95.71 * $178.164247 = $17,051.74/day
```

Fee revenue comparison at current share:

| Fee | Current model price revenue/day | 12m forward revenue/day |
| ---: | ---: | ---: |
| 0.25% | $1.32 | $42.63 |
| 0.50% | $2.64 | $85.26 |
| 0.75% | $3.96 | $127.89 |
| 1.0% | $5.28 | $170.52 |
| 1.5% | $7.92 | $255.78 |
| 2.0% | $10.56 | $341.03 |
| 2.5% | $13.19 | $426.29 |

The absolute fee revenue at small pool share is not enough to justify adding a
BTX Start platform fee during onboarding. If the 12-month forward price path
materializes, any future fee revenue grows mainly through price and pool-share
growth, so the better near-term objective is maximizing miner adoption and
retained hashrate.

## Recommendation

Current BTX Start platform fee:

```text
0.00% = 0 bps
```

Future fee activation should follow `REVENUE_MODEL.md` and
`backend/platform-revenue-policy.example.json`. In short: keep the platform fee
at `0 bps` until BTX Start controls stratum, payout policy, fee routing, the
public fee address, and a per-wallet dashboard with payout history.

Reasoning:

- The immediate product goal is miner activation, not fee extraction.
- New miners need a clear path: add address, run preflight, install, confirm
  shares, confirm GPU work, and check balance commands.
- A zero BTX Start platform fee is easier to understand than a promotional fee
  ladder.
- Fee policy should not be revisited until BTX Start owns the backend, fee
  routing, and first-party per-wallet dashboard.
- Optional premium tools should be monetized separately from mining payouts
  where possible: fleet alerts, rig analytics, CSV exports, and managed setup
  support.

## Competitive Positioning

The offer should be simple:

```text
0.00% BTX Start platform fee during onboarding.
Customer mines to their own BTX address.
Preflight before install.
Visible share, GPU, balance, block-credit, and aggregate stats signals.
Open-source miner.
```

This is more compelling than competing on fee math because it removes friction:
miners can focus on starting and observing the mining process.

## Implementation Note

This repository is a static GitHub Pages starter site plus the miner client.
It does not contain the live pool server configuration. The static site can
show the recommendation, but the real pool fee remains whatever
`https://api.drinknile.com/stats` reports as `policy.pool_fee_bps`.

The live backend also controls where the fee goes. The first-party launch
policy is zero fee. The installer has been pointed at
`stratum.drinknile.com:3333` so there is no migration from the old pool later,
but public mining should wait until `scripts/verify-owned-backend.sh` passes
against the production backend.

BTX Start platform fee is currently 0.00%. If a platform fee is later enabled,
it should route to a dedicated public platform treasury wallet, not a personal
day-to-day wallet. The intended use would be infrastructure, security, miner
tooling, and collectively selected new BTX projects. This treasury would not
create miner ownership, dividends, or profit-sharing claims.

To actually change the live pool fee, update the pool backend policy/config to:

```text
pool_fee_bps = 0
```

Then confirm the change with:

```bash
curl -s https://api.drinknile.com/stats | jq '.policy.pool_fee_bps'
```
