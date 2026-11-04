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

## Independent-review corrections

The original implementation's nonfinite-action failure, blind free-text leakage, test-to-real relabelling, and unchecked saved-request mutation were reproduced against b4b99e3 using synthetic regression fixtures. See validation/review-before.txt. No actual model or participant data were used.

- Invalid actions, including NaN, Infinity, -Infinity and numeric overflow 1e309, consume a command and preserve the canvas. Event/history action is null; the exact original provider body remains in the immutable response log and is referenced by the event.
- Blind action exports allow only validated draw geometry, undo and stop; invalid commands expose only command index, validity and a null action. Raw errors, explanations, extra fields and provider metadata remain private. Inconsistent records fail closed.
- Manifest and every response retain execution provenance. Resume with another source/endpoint is rejected; summary classification is derived from recorded response provenance. Blinding, analysis and cost estimation independently verify that provenance. Changing a summary label cannot promote a technical fixture.
- Audit schema 2 freezes application-code hashes, Python/package versions, DiffVG binding hashes and compiled-renderer hash. Pending/request/response/receipt links are checked, including exact canonical file bytes and regenerated requests. Changed/missing records, version drift and changed canvases stop execution without overwriting the discrepancy or making a new call. Final artifact hashes are checked before blind export.
- A shared development/evaluation registry captures all declared targets, template IDs, original image/demo hashes and demonstration content before any campaign call. Missing either set, overlaps across separate input files, changed unstarted assets and mismatched supplied targets fail closed. Formal campaigns require the identical registry from a complete real-model pilot, and user approval must include materials_sha256. This establishes isolation within the declared study universe; it cannot attest that undeclared external files do not exist.
- Adjacent same-size images exist at production transition boundaries. docs/MULTI_IMAGE_ACCEPTANCE.md records version-specific upstream reports and a real two-image identity/order gate. The offline diagnostic generator makes zero model calls, adds no production separator and labels its stimuli as technical, not human demonstrations. The reported serving issue has not been reproduced on an actual target deployment here.

Legacy logs lacking schema-2 provenance/receipts cannot be automatically resumed, relabelled or exported as real evidence; preserve them for explicit manual review. Local hashes detect inconsistent/changed records; they are not external provider attestation or a signature against an actor able to rewrite every local record.

Latest native validation: 43 tests passed. The Docker check mounts the updated source read-only into the previously verified dependency image, runs the same tests and checks the updated CLI help; it is not a claim that a new standalone image was rebuilt. Exact outputs are recorded in validation/review-native-tests.txt and validation/review-docker-tests.txt. No live VLM calls or formal experiments were performed during these corrections.

## Follow-up audit corrections

Eight regression cases failed against c7faa0c: integer-coordinate overflow (10^400), the JSON parser's integer-string limit (5,000 digits), and undetected edits to event actions or summary condition/invalid/completion/target/stop-reason fields. Evidence is in validation/review2-before.txt.

Coordinate validation now checks the normalized range before float finiteness, avoiding conversion overflow. Model-action decoding catches integer-limit ValueError as an invalid command without relaxing Python's parser limit. Raw response bodies remain unchanged; both cases consume exactly one command, preserve the canvas, and resume without extra calls.

Execution and audit now share response_to_event. Audit replays all original responses in order, requires a matching event for every response, rejects actions after stop/budget and incomplete sequences, and derives commands, invalid count, stop reason, classification and run/target/condition from replay and the frozen manifest. It compares the complete canonical saved summary, retaining completion=None until separate human evaluation. Blind preparation and analysis reject inconsistent events/summaries before creating exports and do not modify the source records.

Latest validation: native 57 passed (4.34 s); Docker 57 passed (4.41 s), using the updated source mounted read-only in the previously verified dependency image, without rebuilding a standalone image. Tests include direct audit rejection plus blind/analysis rejection, and verify that original raw responses and altered evidence remain preserved. See validation/review2-native-tests.txt and validation/review2-docker-tests.txt. All fixtures are synthetic; real-model calls and experiment API spend remain zero.

## Standalone rebuild and CPU deployment preparation

The final application code at 0d45a28d46342f5bb8270e4a01ed75189675df39 was rebuilt from the repository Dockerfile into standalone image sha256:f85543e9f4fff7f89f616e3fd2a4d327417d365c7dace46aebef94d726739e97. Its own embedded source passed all 57 tests in 5.69 s, without a source bind mount. See validation/standalone-final-tests.txt. This supersedes the earlier mounted-source-only validation limitation. The subsequently added Ubuntu guide and metadata are repository deliverables; they are not claimed to be embedded in that image.

llama.cpp v0.8.0 commit 8642541b255bfb5dc39cd351a178be09013a55d6 also compiled successfully as a CPU-only llama-server in this cloud environment. The binary reported `0.8.0-dev (build 1, commit 8642541)` from the shallow tagged checkout, with GNU 14.2.0 on Linux x86_64. Version/help were executed and the documented CPU/auth/template flags verified. See validation/llama-cpu-build.txt and validation/llama-cpu-version.txt. No model was loaded and no inference server was started; this is engine build evidence only, not a model compatibility or throughput test.

[UBUNTU_CPU_PILOT.md](UBUNTU_CPU_PILOT.md) pins the proposed official Qwen3-VL-4B Q4_K_M weights/projector and llama.cpp version, provides byte verification, private loopback service, actual identity/order diagnostics, resource/failure recording, pilot gates and stop/cleanup procedures. Model SHA-256 values are from official metadata; downloaded-byte verification is still pending. configs/qwen3vl4b-candidate.sha256 supplies the reviewed expected hashes. The user has not selected the candidate or authorized access, installation or execution on their machine. Actual CPU, operating-system version, context fit, multi-image behavior and performance remain unverified. All prior real-pilot/material/approval blockers remain; real model calls and experiment API spend are still zero.
