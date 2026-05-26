# Billing Model

BTX Start has two possible monetization paths:

1. **Backend payout-accounting fee**: the current model. Each payout address
   gets a 7-day 0.00% fee trial. After the trial, the pool backend deducts a
   disclosed percentage from mined BTX and routes it to the public platform
   fee wallet.
2. **Credit-card membership**: optional fiat billing for premium features.

The recommended split is:

- Keep mining itself near-zero friction: no account, no card, no custody.
- Use the disclosed post-trial BTX pool fee for base mining economics.
- Add credit-card membership only for extras: richer dashboard history,
  alerts, CSV exports, rental GPU workflow automation, priority support, and
  API access.

## Why not make card membership required to mine?

Required card billing would add account creation, identity, subscription
state, payment failures, cancellations, support load, chargeback risk, and
access-control logic before a miner has proven the install works. That works
against the current product goal: get someone mining to their own wallet with
as little friction as possible.

It also creates an enforcement problem. A card-based trial only matters if the
stratum backend refuses unpaid miners after the trial. That means the pool
must replace address-only auth with signed account tokens or subscription
lookup at `mining.authorize`, which is a larger backend change than payout
accounting.

## Recommended membership product

Base mining:

- No account required.
- 7-day fee-free trial by payout address.
- 0.50% disclosed post-trial BTX fee through backend payout accounting.

Optional Pro:

- 7-day card-backed trial.
- Low monthly fiat price.
- Premium dashboard history.
- Email or webhook alerts.
- Vast.ai rental tracking.
- CSV exports.
- Multi-rig labels and uptime reporting.
- API access for power users.

## Required backend pieces for card billing

GitHub Pages cannot securely collect or process cards. Card billing requires a
backend service with:

- Payment processor secret key stored server-side only.
- Checkout session creation endpoint.
- Subscription/customer database.
- Webhook endpoint that verifies processor signatures.
- Customer portal or cancellation flow.
- Mapping between user account, payout addresses, and dashboard access.
- Terms shown before trial starts, including trial length, price after trial,
  renewal cadence, cancellation path, and what happens to base mining access.

## What should be enforced by card status?

Do not gate base mining on card status at launch. Gate only premium features:

- `free`: can mine, see public stats, use command generator.
- `trialing`: can use Pro dashboard features.
- `active`: can use Pro dashboard features.
- `past_due` / `canceled`: falls back to base dashboard and base mining.

This keeps miner trust clear: their BTX payout address is still theirs, mined
BTX is not held hostage, and the card product is an optional service layer.
