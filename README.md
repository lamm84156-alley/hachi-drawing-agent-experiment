# Hachi drawing-agent experiment

Implementation of *The Effect of Demonstration Order on Drawing Agent Performance*. See [design and unresolved choices](docs/PROTOCOL.md). No real experimental results or human ratings are bundled.

## Technical acceptance

```sh
sh scripts/docker_acceptance.sh
```

This builds the CPU DiffVG image and runs isolated synthetic software tests. It makes no model API calls. A local alternative is Python 3.12, `pip install -r requirements.lock --extra-index-url https://download.pytorch.org/whl/cpu`, `sh scripts/install_diffvg.sh`, `pip install --no-deps -e .`, `python -m pytest -q`. The installer uses /tmp/hachi-diffvg and expects that destination to be absent.

DiffVG commit is pinned, with pybind11 v2.13.6 for Python 3.12 and CMake <4. This build-only compatibility update changes no research condition. Rendered experimental observations always use DiffVG; SVG export preserves editable geometry.

## Materials and protocol

Use `scripts/record_demo.html` locally to manually record connected cubic paths. The displayed 256px/2px settings are interface examples, not frozen study values. Record one face per target with the same human demonstrator. Programmatic test fixtures must never be used as human evidence. Target PNGs must match frozen resolution. Store target records in a JSON array with `id`, `template_id`, `split` (`development`/`evaluation`), `image` (PNG path), `prompt`, and `demo` (record JSON path). Development and evaluation template IDs must be disjoint. Use paths relative to the execution working directory or absolute paths available inside the container.

Fill all null fields in configs/protocol.json after pilot decisions. Preserve frozen copies and human provenance. Supply model credentials via the environment's secret configuration as HACHI_API_KEY, never chat, Git, or command-line arguments. Allow the selected provider HTTPS hostname in the environment network policy. For dot or Ubuntu CPU self-hosting, see [local VLM options and measured resource limits](docs/LOCAL_VLM.md). The API adapter requires a frozen returned model identifier; aliases that resolve to another identifier are rejected.

```sh
hachi freeze-materials materials/development.json materials/evaluation.json private/materials.json
hachi plan materials/development.json private/pilot-plan.json --stage pilot --repeats 1 --seed 20261104
# After explicit API cost approval and protocol freeze only:
hachi run private/pilot-plan.json materials/development.json configs/protocol.json private/pilot-authorization.json runs/pilot --materials-manifest private/materials.json --endpoint https://PROVIDER/CHAT_COMPLETIONS_PATH
```

Create the parent directory first. Authorization JSON requires `approved_by_user: true`, `api_spending_approved: true`, `approval_reference`, `stage`, and SHA256 hashes `plan_sha256`/`protocol_sha256` from `hachi.design.digest` of parsed JSON, plus `materials_sha256` from the frozen shared registry. Pilot and formal stages must use that same registry; formal execution also requires `--pilot-campaign runs/pilot/campaign.json` pointing to a complete real-model pilot with the identical registry. This records an actual user approval; do not fabricate an authorization file. No approval is bundled. Formal runs need separate approval after real pilot results and cost review.

## Resume and audit

Repeat the identical run command. Per-run lock prevents concurrent mutation. Frozen manifest detects input, execution-source, code and renderer changes. Every response carries its original provenance and request/runtime hashes; immutable receipts bind response bytes to requests. Resume verifies saved request hashes and regenerated packets, and refuses changed/missing records. Legacy logs without these records require manual review; they are never automatically promoted or relabelled. Every command saves the full image-bearing request, raw response, model ID, usage, action, validation outcome, and SVG/PNG state. Completed responses replay without new API calls only after these checks pass. Invalid model content is represented as a null action plus validation status in history; its exact original content remains in the saved raw response referenced by the event. Blinded exports contain only validated geometry/operations or null for invalid commands; model explanations and extra fields remain private. A pending request without a response is an uncertain outcome and stops automatic retry; reconcile with the provider before any manually authorized retry. Provider failures are retained and halt the schedule. Do not delete logs to force success. Failed/incomplete runs remain visible and must be resolved/reported before complete-case analysis.

Raw model response bodies may contain user content; keep runs private. Request files contain base64 images, not API credentials. Disk consumption grows with full-context image requests.

## Evaluation and outputs

Follow [the blind-review guide](docs/RATING_GUIDE.md). After genuine complete labels:

```sh
hachi blind runs/pilot private/blind-pilot --seed 42
hachi analyze runs/pilot private/ratings.csv artifacts/pilot --seed 42
python scripts/estimate_cost.py runs/pilot --input-per-million PRICE --output-per-million PRICE
```

Analysis emits runs.csv, statistics.json, completion.svg, completion.pdf and report.md. It rejects technical-test logs and absent labels. Bootstrap and agreement code have mathematical fixture tests; those fixtures are never research outputs. Part annotation and redraw tables are prepared; full secondary aggregation awaits the frozen rubric. No empirical statistics or result plots are generated before real observations exist.

54 runs × 40 commands = at most 2,160 action calls (300-run design: 12,000), excluding separately authorized retries. Currency estimates require a chosen model, current verified provider rates and real usage across all pilot conditions. The cost helper uses actual logged prompt/output tokens, including provider-counted image tokens, and does not assume discounts. It is an estimate, not a hard spend cap; configure a provider-side spending limit.

Secondary annotation export is available through `hachi.analysis.export_secondary(parts_csv, redraws_csv, output_directory, width, height, frozen_layout_threshold)`. It exports normalized per-part errors and redraw criterion failures from actual human annotations; omission flags remain explicit. The scalar layout formula must be frozen and used by raters before supplying before/after errors.

After building, `sh scripts/docker_run.sh --help` runs the CLI in Docker. Replace `--help` with a reviewed `plan`, `run`, `blind` or `analyze` command. It mounts the repository at /work for relative material/output paths, preserves configured proxy trust, inherits HACHI_API_KEY without printing it, and maps writes to the invoking host user (root inside a rootless daemon, invoking UID otherwise). For a CPU server on Ubuntu, running the model and experiment directly on that same machine avoids cross-container loopback ambiguity. `python scripts/hardware_check.py` records a read-only hardware snapshot without loading any model.

Before any campaign, `freeze-materials` requires both complete development and evaluation lists, checks template isolation across them, and snapshots every target record, demonstration and image hash. The run command rechecks the entire registry, including unstarted targets, before each episode. Missing cross-set evidence blocks execution. Updating the material universe requires a newly frozen registry and a matching new approved pilot; separate unrelated manifests cannot silently satisfy the formal-stage gate. This check covers the declared study universe, not unknown files outside it.

For reported same-size adjacent-image risks in some Qwen serving versions, see [real-model identity/order acceptance](docs/MULTI_IMAGE_ACCEPTANCE.md). The offline probe generator makes no inference calls and does not change production separators or demonstration semantics.
