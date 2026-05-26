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
- Added `stats-snapshot.json` plus a GitHub Action so the page reads stats from
  our own origin rather than sending every browser directly to the current
  backend stats API.
- Added an operating-status section that separates "can mine now" from
  "BTX Start receives the fee."
- Added a personal tracker section with copyable commands for worker id, local
  miner logs, GPU utilization, Telegram balance, Telegram block credit, and
  aggregate pool stats.

## Next backend work

These are the changes needed to become independent rather than just a better
frontend:

- Publish BTX Start release artifacts for `btx-gbt-solve`, `SHA256SUMS`, and
  package source.
- Deploy a BTX Start stratum endpoint.
- Deploy a BTX Start stats API and payout index.
- Deploy a BTX Start Telegram or web balance bot.
- Set the backend pool fee policy to the launch target, `pool_fee_bps = 50`.
- Replace the installer default pool host with the BTX Start stratum host.
- Build a first-party per-wallet dashboard backed by our own share/payout index.

Until those are deployed, the honest user experience is: BTX Start controls the
onboarding page, installer entrypoint, docs, and package fork. The mining
backend, fee destination, Telegram balance bot, per-wallet web dashboard, and
solver release artifacts are still dependencies.
