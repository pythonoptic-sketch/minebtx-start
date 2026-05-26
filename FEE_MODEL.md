# BTX Pool Fee Model

Snapshot inputs, fetched May 26, 2026:

- Public page: https://pythonoptic-sketch.github.io/minebtx-start/
- Pool stats: https://stats.minebtx.com/stats
- BTX price model: https://btxprice.com/api/current.json
- BTX forward model docs: https://btxprice.com/forward-market-price.md

## Current Observed State

From `stats.minebtx.com/stats`:

- Current published pool fee: `250 bps` = `2.50%`
- Active workers now: `9`
- Active workers, 24h: `15`
- Pool share of network: `0.498%`
- Network hashrate: `2.27M n/s`
- Current fee address:
  `btx1zqzv4vgyhzyqqrkccxre0r4wgq9awwp6kjsdj6n8tfa0em0lfm22safa89n`
- Current treasury address:
  `btx1zatnjdqpw4cjswjeajst5lkj8mrdsj8mhgzu3emycncuctfrtqmzst94c6s`

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

The absolute dollar difference between `0.50%` and `2.50%` is currently about
`$10.56/day` at current model price and current pool share. That is not enough
to justify being fee-average during launch. If the 12-month forward price path
materializes, fee revenue grows mainly through price and pool-share growth, so
the better near-term objective is maximizing miner adoption and retained
hashrate.

## Recommendation

Recommended launch fee:

```text
0.50% = 50 bps
```

Recommended launch schedule:

```text
Pool share below 1.0%:      0.50%  (50 bps)
Pool share 1.0% to 2.0%:    1.00%  (100 bps)
Pool share 2.0% to 5.0%:    1.50%  (150 bps)
Stable retained pool:       2.00%  (200 bps)
```

Upper bound while still growing:

```text
2.50% = 250 bps
```

Avoid for now:

```text
> 2.50%
```

Reasoning:

- BTX is early and pool share is under 1% of network hashrate.
- Miner switching cost is low, so fee elasticity is likely high.
- The 12-month price model implies revenue upside comes more from network and
  pool-share growth than from extracting another 50 bps today.
- A lower fee improves the visible value proposition for new miners.
- Public mining-pool fee references commonly sit around `0.25%` to `2%`.
  To be clearly more attractive, the launch offer should be near the low end,
  not merely average.

## Competitive Positioning

The offer should be simple:

```text
0.50% launch fee while the pool is below 1% network share.
Weekly payouts.
No minimum beyond dust.
Published fee and treasury addresses.
Open-source miner.
```

This is more compelling than competing on claims like "fast" or "community"
alone because it directly improves the miner's expected net payout.

## Implementation Note

This repository is a static GitHub Pages starter site plus the miner client.
It does not contain the live pool server configuration. The static site can
show the recommendation, but the real pool fee remains whatever
`stats.minebtx.com/stats` reports as `policy.pool_fee_bps`.

To actually change the live pool fee, update the pool backend policy/config to:

```text
pool_fee_bps = 50
```

Then confirm the change with:

```bash
curl -s https://stats.minebtx.com/stats | jq '.policy.pool_fee_bps'
```
