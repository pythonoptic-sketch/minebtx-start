# Article-Derived Improvement Opportunities

Source set reviewed:

- [Whyte: The agent that pays its own way](https://whyte.biz/articles/ai-agents-mine-btx)
- [Whyte: BTX goes live](https://whyte.biz/articles/btx-post-quantum-settlement)
- [Whyte: When software spends](https://whyte.biz/articles/settlement-for-autonomous-agents)
- [Whyte: Proof of Useful Work](https://whyte.biz/articles/proof-of-useful-work)
- [BTX Mine operator page](https://btx.dev/mine/)
- [BTX mining docs](https://btx.dev/docs/node/mining/)
- [BTX mining RPC docs](https://btx.dev/docs/rpc/mining/)
- [BTX developer challenge page](https://btx.dev/develop/)

## Core Read

The useful shift in the articles is not "BTX is an AI coin." The actionable
shift is that the miner should become an agent-operable compute workload:
installed, verified, scheduled, monitored, and paid out through interfaces that
software can inspect without a human dashboard.

For this repository, the strongest improvements are therefore not more landing
page copy. They are control-plane features that let an agent or fleet manager
make correct decisions about GPU cycles, pool health, payout safety, and whether
mining should yield to inference.

## Priority Implementation List

### 1. Add `dexbtx-miner doctor --json`

Why:
The article's operator loop starts with install and verification. The current
installer does important checks, but an agent needs a command it can run again
after deploy, reboot, or drift.

Implement:

- Verify config loads and required keys are present.
- Verify payout address shape, at minimum `btx1z...`.
- Verify solver binary exists and is executable.
- Verify solver supports required patched flags: `--daemon` and `--share-target`.
- Verify expected SHA256 against `pyproject.toml`.
- Verify pool TCP/TLS reachability.
- Emit both human text and machine-readable JSON.

Acceptance criteria:

- `dexbtx-miner doctor --config ~/.dexbtx-miner/config.yaml --json` exits 0 only
  when the miner is runnable.
- Failed checks include stable machine-readable codes such as
  `solver_missing`, `bad_payout_address`, `pool_unreachable`.

### 2. Add an idle-cycle scheduler for inference co-location

Why:
The central article thesis is co-scheduling mining into inference troughs rather
than running "two full jobs at once." This repo already slices work in short
solver windows, which is a good base for yielding.

Implement:

- Config keys:
  - `idle_only: true`
  - `gpu_util_max_percent: 65`
  - `gpu_memory_free_min_mb: 2048`
  - `idle_check_interval_s: 2`
  - `resume_after_idle_s: 10`
- NVIDIA path through `nvidia-smi --query-gpu=utilization.gpu,memory.free`.
- Optional process guard such as `pause_when_process_regex`.
- In `_solver_loop`, skip starting a new slice when the GPU is busy.
- Log `mining_paused_busy_gpu` and `mining_resumed_idle_gpu`.

Acceptance criteria:

- When a synthetic high-utilization reading is injected in tests, no new solver
  slice starts.
- Existing stratum reader stays connected while mining is paused.
- Accepted/rejected share counters are unaffected by pause/resume.

### 3. Publish a local machine-readable health endpoint

Why:
The articles emphasize monitoring through `getmininginfo`, `getnetworkhashps`,
and `getdifficultyhealth`. A pool miner cannot call every node RPC directly, but
it can expose its own control-plane state to an agent.

Implement:

- `--health-port 0|<port>` config/CLI option.
- HTTP JSON endpoint with:
  - connected/disconnected
  - current job id and age
  - accepted/rejected/block counters
  - reject code counts if available from pool errors
  - last share time
  - solver slice latency
  - current nonce position
  - current pause reason
- Keep it local-only by default: `127.0.0.1`.

Acceptance criteria:

- `curl localhost:<port>/healthz` returns 200 when connected and solving.
- `curl localhost:<port>/metrics` returns stable JSON for agent polling.
- No payout address is exposed unless `expose_identity: true`.

### 4. Add pool and network economics telemetry

Why:
The "Difficulty Commons" argument says agents need a live signal for whether a
spare GPU cycle is worth mining. The current website shows a few pool metrics,
but the miner has no decision model.

Implement:

- `dexbtx-miner economics --json`
- Pull pool stats from `https://stats.minebtx.com/stats` when available.
- Include network hash, pool share, active workers, blocks found, expected
  payout pool, fee, and tip age.
- Optional local inputs: power watts, electricity price, GPU hourly opportunity
  cost.
- Output `mine`, `pause`, or `unknown` with the assumptions used.

Acceptance criteria:

- The command works without a solver binary.
- If stats fetch fails, output is `unknown` with a clear reason.
- The calculation is explicit enough for an agent to audit.

### 5. Tighten payout and treasury safety

Why:
The articles repeatedly point to post-quantum payout rails and bounded treasury
assumptions. This pool client currently requires a payout address but does not
validate or explain treasury policy beyond comments.

Implement:

- Validate configured address prefix and obvious malformed values.
- Warn when using placeholder addresses.
- Add docs for descriptor wallet creation and operational payout hygiene.
- Add a `--dry-run-config` path that prints the fully resolved worker identity
  without connecting to the pool.

Acceptance criteria:

- Placeholder config refuses to start.
- Invalid address emits a specific error before networking starts.
- Docs explain recommended worker names and payout address handling.

### 6. Add an "agent launch kit" page to the website

Why:
The public site should match the strongest differentiated narrative from the
articles: this is a miner an autonomous operator can run and monitor.

Implement:

- A page or section covering:
  - install and verify
  - co-schedule idle GPU cycles
  - monitor as JSON
  - settle to post-quantum payout addresses
- Link to Whyte's article, BTX mining docs, mining RPCs, and btx.dev/develop.
- Keep it practical, not promotional: describe what exists and what is roadmap.

Acceptance criteria:

- The first screen still remains mining-focused.
- The agent section links to concrete docs and avoids implying idle scheduling
  exists until it is implemented.

Status:
The homepage now has a first-pass "Agent-ready mining" section. The deeper
feature work remains to be implemented in the miner.

### 7. Add service-challenge examples as a separate integration track

Why:
The BTX developer docs describe challenge-gated routes for AI/API gateways.
That is adjacent to mining, not part of the pool client, but it is a credible
expansion path for the site and docs.

Implement:

- `examples/service_challenge_gateway/`
- Minimal FastAPI or Node gateway pseudocode made runnable.
- Shows issue challenge, solve client-side, redeem proof, then allow an
  expensive route.

Acceptance criteria:

- Example can run in local mock mode without a BTX node.
- Real mode documents required BTX RPC methods and expected responses.

## Recommended Sequence

1. Implement `doctor --json`.
2. Implement local health endpoint.
3. Implement idle-cycle scheduler.
4. Add economics telemetry.
5. Add payout validation and treasury docs.
6. Expand the website into a dedicated agent launch path.
7. Add service-challenge examples after the mining control plane is solid.

That sequence matches the agent loop from the article: verify first, observe
second, schedule third, then optimize economic decisions.
