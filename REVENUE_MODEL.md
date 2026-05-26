# BTX Start Revenue Model

BTX Start uses a per-payout-address trial. The current target policy is:

```text
first 7 days from first accepted share: 0.00% = 0 bps
after day 7: 0.50% = 50 bps
```

The platform should not mark this live until BTX Start controls the backend
that can route fees, accumulate them in the public fee wallet, and show each
miner what happened.

## Near-Zero-Friction Rules

- No account required.
- No email required.
- No chat app or bot required.
- No custody of miner funds.
- No wallet connection.
- One payout address plus one command.
- Worker name is optional and defaults to `default`.
- The page does not store visitor input.
- Fee-free trial starts at the first accepted share for that payout address.

## Activation Gates

The post-trial platform fee should only be enabled after all of these are true:

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
First 7 days per payout address:      0.00%  (0 bps)
After dashboard + public fee wallet:  0.50%  (50 bps)
After retained pool + payout history: 1.00%  (100 bps)
```

Stay below the existing backend-reported fee until the product has clear
retained hashrate, public payout history, and visible operating costs.

## Fee Routing

The primary fee mechanism should be backend payout accounting:

```text
gross miner reward -> deduct platform fee after trial -> miner payout
                                      |
                                      v
                             public fee wallet
```

Do not rely on hidden miner-side compute diversion as the primary mechanism.
Miner-side "dev fee" switching is easier to bypass, harder to audit, and less
transparent than backend payout accounting.

## Premium Revenue

Paid features should be optional and separate from mining payouts:

- Fleet uptime monitoring.
- GPU efficiency reports.
- Payout and tax CSV exports.
- Rig offline alerts.
- Managed setup support.

The default miner path should remain simple: paste address, copy command, mine
to your own wallet.
