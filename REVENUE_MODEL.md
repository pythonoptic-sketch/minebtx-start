# BTX Start Revenue Model

BTX Start is zero-fee during onboarding. The current platform fee is:

```text
0.00% = 0 bps
```

The platform should not charge until BTX Start controls the backend that can
actually route fees and show each miner what happened.

## Near-Zero-Friction Rules

- No account required.
- No email required.
- No chat app or bot required.
- No custody of miner funds.
- No wallet connection.
- One payout address plus one command.
- Worker name is optional and defaults to `default`.
- The page does not store visitor input.

## Activation Gates

A future platform fee should only be enabled after all of these are true:

- BTX Start stratum endpoint is live.
- BTX Start payout policy and fee routing are deployed.
- Dedicated public platform fee address is created and published.
- Per-wallet dashboard shows worker state, shares, balances, and payouts.
- At least one payout cycle has public history.

## Revenue Formula

```text
platform revenue/day =
19,200 BTX/day * pool_share * platform_fee * BTX_price
```

BTX emits approximately:

```text
20 BTX/block * 960 blocks/day = 19,200 BTX/day
```

## Fee Schedule

```text
Before backend ownership:             0.00%  (0 bps)
After dashboard + public fee wallet:  0.50%  (50 bps)
After retained pool + payout history: 1.00%  (100 bps)
```

Stay below the existing backend-reported fee until the product has clear
retained hashrate, public payout history, and visible operating costs.

## Premium Revenue

Paid features should be optional and separate from mining payouts:

- Fleet uptime monitoring.
- GPU efficiency reports.
- Payout and tax CSV exports.
- Rig offline alerts.
- Managed setup support.

The default miner path should remain simple: paste address, copy command, mine
to your own wallet.
