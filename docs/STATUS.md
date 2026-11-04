# Technical acceptance status — 2026-11-04

No real VLM was invoked. API calls: 0; model API spend: 0. No human scores, empirical effect estimates, or research result plots have been created. No 54-run or 300-run experiment was started.

## Implemented

- Python connected cubic-path drawing/undo/stop validator; invalid commands consume the 40-command budget.
- Actual CPU DiffVG raster feedback plus editable SVG output. Pinned DiffVG commit 85802a71fbcc72d79cb75716eb4da4392fd09532; pybind11 v2.13.6 and explicit Python include-directory build fixes.
- Original, Reordered and No Demo scheduling, seeded non-original permutations, complete cumulative demonstration replay and no-demo omission.
- Frozen protocol/plan/campaign identity; single demonstrator and disjoint template checks; randomized run order and supported execution seeds.
- API and self-hosted Chat Completions transports, full multimodal requests, strict action parsing, raw response/model/version/usage/latency and per-command SVG/PNG audit files.
- File-locked resume replays saved responses; uncertain outbound requests and provider errors halt instead of automatically repeating paid calls.
- Explicit user-approval records required for pilot spending/local deployment and separately for formal execution.
- Human recording interface, condition-blind packets and unfilled rating/part/redraw templates. Discussion/adjudication preserves original independent ratings.
- CSV, SVG/PDF and Markdown report generation from real-model logs plus genuine human labels; raw agreement, Cohen's kappa and 10,000 paired whole-target bootstrap. Full planned campaign required to prevent silent omission of unstarted/failed runs.
- Per-part normalized bounding-box/center errors and redraw criterion export from actual human annotations; no invented scalar layout metric.
- Docker build/run scripts, pinned Python dependency lock, hardware snapshot utility, reproduction and model-access guides.

## Verified evidence

See validation/native-tests.txt and validation/docker-tests.txt for the final execution summaries. Native tests exercise real DiffVG rendering, non-white output, reordered final-image equality, full-context image counts, no-demo omission, malformed-output exhaustion at 40 commands, undo/stop, immutable resume, uncertain-call blocking, model-version mismatch, mathematical bootstrap/agreement fixtures and endpoint rules. Test transports and synthetic geometry are explicitly technical fixtures, not research data.

The first Docker image built and passed 16 tests. A later layered rebuild exhausted the 32 GB workspace under Docker's vfs storage driver. Task-created build caches and the obsolete image were removed; Dockerfile was consolidated to avoid repeated dependency-tree copies. The compact build and final-source validation are recorded separately. This recovery did not delete research data; none existed.

## Remaining blockers and decisions

1. Source archive: final PDF v19 and editable Markdown v1 were fully read through Library, but supported prepare_materialize + helper downloads both returned `library file transfer failed: download failed`. No original local bytes/xattrs were installed. This was a failed transfer, not an automatic approval denial. Library download host is absent from the environment's explicit allowlist; precise transfer error was not exposed. Do not assert a local PDF checksum or original-file archive exists.
2. Real pilot: no selected model, configured API credentials, approved model spending/deployment, model weights or human demonstration/target set. Model API and model-hosting domains are absent from the active network allowlist. No call/download was attempted to bypass that policy.
3. Freeze model/decoding/resolution/pen/history/context limits, per-part rubric tolerances and scalar layout definition/threshold on development tasks. Current null configuration fields intentionally block runs.
4. Decide 54-run target/repetition allocation (product must be 18). Preserve all three conditions and 40 commands. Formal authorization must follow real pilot results and costs.
5. Dot hardware: effective 16 GiB RAM, 4 CPU equivalents, no exposed GPU. CPU model inference, many-image context fit, throughput, peak RAM and long-job lifetime remain unverified. The separate Ubuntu/128 GB/no-GPU/possible ninth-generation i9 machine is user-reported only; no connection or installation was attempted.
6. No empirical API estimate yet. Upper action-call count is 2,160 for 54 runs versus 12,000 for 300, before separately approved retries. Monetary estimate needs current chosen-model tariffs and real pilot token usage. Self-hosted inference replaces token fees with hardware/runtime cost; no free-infrastructure claim is made.

The repository is a tested technical foundation. A real-model pilot and scientific evaluation are pending, not passed.

Final evidence: native suite 20 passed; compact-image suite 20 passed; final source overlay image `sha256:6eb411262354dfbf0f39022b954b60e299e27b624d1bafd91a981ccd76e6d638` also passed 20 tests (2.61 s test time, excluding container startup). Final image was produced by copying the current repository onto the freshly built compact image; the repository Dockerfile builds the same dependency/source combination from scratch. At this point about 21 GB was free; future model capacity must be rechecked, because vfs container creation itself copies image contents. Docker CLI smoke-test output is stored in validation/docker-cli.txt.

The Docker CLI smoke test initially failed because numeric host UID 1000 inside a rootless Docker namespace maps to a subordinate user and could not read /app. scripts/docker_run.sh now detects rootless mode and uses container UID 0 (mapped to the host task user); rootful mode retains the invoking UID. The corrected wrapper exited 0 and printed the CLI help, recorded in validation/docker-cli.txt. Dockerfile also makes /app readable for rootful non-root runs; that rootful variant was not separately exercised. Final free workspace space after stopped containers were removed: about 23 GB.
