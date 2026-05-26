# BTX Start Improvements From v4.3-sm89-native

Source reviewed: https://github.com/dexbtx/minebtx/releases/tag/v4.3-sm89-native

## Release facts that matter

The release already removes one major barrier: miners should not need to build
BTX source locally. It ships a patched `btx-gbt-solve` binary, optional node
tarball, legacy solo-miner script, and `SHA256SUMS`.

The important solver changes are:

- `--share-target`, which makes pool mining practical because the solver can
  stop once it finds a share-level digest.
- `--daemon`, which keeps CUDA context alive across slices and avoids repeated
  process startup cost.
- GPU artifact coverage for Pascal, Ada, Hopper, and Blackwell, with PTX JIT
  fallback for Turing and Ampere.

## First-principles onboarding model

A new miner does not start from "what release artifact exists?" They start from
five questions:

1. Can my machine run this?
2. Will the script change my system?
3. Will I mine to my own address?
4. How do I know the binary is the intended binary?
5. How do I know the GPU is actually doing work?
6. Where does the pool fee go?
7. Can I visually follow my own miner after launch?

The original one-line installer mostly answered those questions after install
had already begun. BTX Start should answer them before installation.

## Implemented now

- Added `install.sh --preflight`.
- Added a public preflight command before the install command.
- Added a compatibility section with the release's GPU execution paths.
- Kept installer/source links inside the BTX Start repo and site.
- Changed the Python package install default to the BTX Start fork instead of
  the upstream source tarball.
- Kept the solver binary as an explicit backend/artifact dependency until BTX
  Start publishes its own signed release artifacts.
- Added `stats-snapshot.json` plus a GitHub Action that targets the
  first-party stats API and leaves the provisioning snapshot in place until
  `https://api.drinknile.com/stats` is live.
- Added an operating-status section that separates first-party backend
  provisioning from wallet ownership and fee policy.
- Added `platform-treasury.json` so the public page can show the BTX Start fee
  wallet status, target fee, intended use of funds, and wallet balance once
  connected.
- Added `scripts/create-platform-fee-wallet.sh` for creating the dedicated
  platform fee address with `btx-cli` on the backend custody machine.
- Added a personal tracker section with copyable commands for worker id, local
  miner logs, GPU utilization, expected-yield math, wallet-balance guidance,
  and aggregate pool stats.
- Added a searchable GPU ranking with starter profiles, estimated hashrate,
  efficiency, and expected BTX/hour from the current network snapshot.
- Promoted the default start flow to one address plus one install command, with
  preflight still available as an optional dry run.
- Added the operating model section: 7-day fee-free trial, backend ownership
  gates, 0.50% post-trial fee, future 1.00% scenario, and optional premium
  tools.
- Added `backend/platform-revenue-policy.example.json` and `REVENUE_MODEL.md`
  so fee activation rules are explicit and machine-readable.
- Pointed the default installer pool at `stratum.drinknile.com:3333` before
  public launch so future miners do not need to migrate from another backend.
- Added `backend/OWNED_BACKEND.md` and `scripts/verify-owned-backend.sh` to
  block cutover unless the first-party stats API, stratum endpoint, trial fee
  policy, and protected personal-address checks pass.

## Next backend work

These are the changes needed to become independent rather than just a better
frontend:

- Publish BTX Start release artifacts for `btx-gbt-solve`, `SHA256SUMS`, and
  package source.
- Deploy a BTX Start stratum endpoint.
- Deploy a BTX Start stats API and payout index.
- Deploy a BTX Start per-wallet web dashboard.
- Set the BTX Start backend policy to a 7-day 0 bps trial and 50 bps
  post-trial fee after all activation gates are complete.
- Keep fee routing disabled until the dedicated public fee wallet and
  per-wallet dashboard are live.
- Build a first-party per-wallet dashboard backed by our own share/payout index.

Until those are deployed, the honest user experience is: BTX Start controls the
onboarding page, installer entrypoint, docs, package fork, and first-party
target hostnames. The stratum process, stats API, payout engine, per-wallet web
dashboard, and solver release artifacts still need production deployment.
