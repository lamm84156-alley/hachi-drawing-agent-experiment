# Ubuntu CPU deployment and real pilot runbook

Status: preparation only. The user has reported Ubuntu, 128 GB RAM, no GPU and a possibly ninth-generation Intel i9. The exact CPU, Ubuntu release and available storage have not been inspected. The user has not selected this model or authorized installation, model downloads or execution on that computer. The commands below are for use **after that approval**. No formal 54-run experiment is included.

## 1. Candidate versions and evidence

| Component | Proposed reproducible candidate |
|---|---|
| Hachi application | `work`, application commit `0d45a28d46342f5bb8270e4a01ed75189675df39`; freeze the eventual checked-out commit and Docker image ID before a run |
| Engine | llama.cpp `v0.8.0`, commit `8642541b255bfb5dc39cd351a178be09013a55d6` |
| Official model repository | `Qwen/Qwen3-VL-4B-Instruct-GGUF` |
| Model repository revision | `1cd86afb9a95c410a6038ab3b40d8b578c892266` |
| Text/model weights | `Qwen3VL-4B-Instruct-Q4_K_M.gguf`, approximately 2.50 GB |
| Matching vision projector | `mmproj-Qwen3VL-4B-Instruct-F16.gguf`, approximately 836 MB |
| Model SHA-256 | `66358cb18bb6b3b1b6675aa412c7a88ef01d228f481184d13668e5201c730a0a` |
| Projector SHA-256 | `256f3a43bd4205ffef48d6b92715e1e70b5b0e9aef06522584967513a9985331` |

The engine tag was resolved with Git and its checked-out source was inspected. The Qwen revision, names, sizes and SHA-256 values were checked against official repository metadata on 2026-11-04; the model bytes have **not** been downloaded or verified locally. The model card identifies Apache-2.0 licensing. Sources: [engine release](https://github.com/ggml-org/llama.cpp/releases/tag/v0.8.0), [official model repository](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/tree/1cd86afb9a95c410a6038ab3b40d8b578c892266), [weight metadata](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/blob/1cd86afb9a95c410a6038ab3b40d8b578c892266/Qwen3VL-4B-Instruct-Q4_K_M.gguf), [projector metadata](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/blob/1cd86afb9a95c410a6038ab3b40d8b578c892266/mmproj-Qwen3VL-4B-Instruct-F16.gguf).

This is a candidate, not a verified model/engine pairing for this experiment. The pinned engine contains Qwen3-VL projector support and CPU serving options, but its mtmd code also retains adjacent-frame merging logic. Do not infer that a newer release fixes every multi-image case. Actual identity/order and full-context acceptance are mandatory. Weight-file size is not peak RAM: KV cache, vision processing, runtime and concurrent processes add memory; throughput on the user's CPU is unknown.

## 2. Inventory and private directories

Run in Bash on the Ubuntu workstation, after approval. Keep models, credentials and runtime records outside Git. Use the same directory variables in each terminal; do not enable shell tracing (`set -x`) or dump environment variables.

```bash
set -euo pipefail
umask 077
export HACHI_REPO="$HOME/hachi-drawing-agent-experiment"
export HACHI_ENGINE="$HOME/.local/share/hachi/llama.cpp-v0.8.0"
export HACHI_MODELS="$HOME/.local/share/hachi/qwen3vl4b-q4km"
export HACHI_STATE="$HOME/.local/state/hachi-cpu-pilot"
mkdir -p "$HACHI_MODELS" "$HACHI_STATE"
chmod 700 "$HACHI_MODELS" "$HACHI_STATE"
mkdir -p "$HACHI_REPO/private" "$HACHI_REPO/artifacts" "$HACHI_REPO/runs"
chmod 700 "$HACHI_REPO/private" "$HACHI_REPO/artifacts" "$HACHI_REPO/runs"
cd "$HACHI_REPO"
python3 scripts/hardware_check.py > "$HACHI_STATE/hardware.json"
lscpu > "$HACHI_STATE/lscpu.txt"
cat /etc/os-release > "$HACHI_STATE/os-release.txt"
free -h > "$HACHI_STATE/memory-before.txt"
df -h > "$HACHI_STATE/disk-before.txt"
git rev-parse HEAD > "$HACHI_STATE/hachi-commit.txt"
```

Check actual CPU model, physical cores, instruction flags, free memory, swap activity and free disk. Reserve space for engine sources/builds, roughly 3.34 GB of selected model files, Docker layers and image-bearing request logs. Do not download all quantizations. Build on this machine with native CPU detection; do not copy a cloud-built native binary to an older i9 or assume AVX-512 support.

## 3. Build the CPU engine and application

The following changes system packages and installs software, so it remains pending owner approval. It assumes an Ubuntu release providing the listed packages; stop if package installation is unsupported instead of replacing repositories automatically.

```bash
sudo apt-get update
sudo apt-get install --no-install-recommends build-essential cmake git ca-certificates libssl-dev curl time
# The destination must not already contain another checkout.
git clone --depth 1 --branch v0.8.0 https://github.com/ggml-org/llama.cpp.git "$HACHI_ENGINE"
test "$(git -C "$HACHI_ENGINE" rev-parse HEAD)" = 8642541b255bfb5dc39cd351a178be09013a55d6
cmake -S "$HACHI_ENGINE" -B "$HACHI_ENGINE/build-cpu" \
  -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON \
  -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_METAL=OFF \
  -DGGML_BLAS=OFF -DLLAMA_BUILD_TESTS=OFF
cmake --build "$HACHI_ENGINE/build-cpu" --target llama-server -j 4
"$HACHI_ENGINE/build-cpu/bin/llama-server" --version > "$HACHI_STATE/engine-version.txt" 2>&1
"$HACHI_ENGINE/build-cpu/bin/llama-server" --help > "$HACHI_STATE/engine-help.txt" 2>&1
sha256sum "$HACHI_ENGINE/build-cpu/bin/llama-server" > "$HACHI_STATE/engine-binary.sha256"
cp "$HACHI_ENGINE/build-cpu/CMakeCache.txt" "$HACHI_STATE/CMakeCache.txt"
```

The baseline explicitly uses CPU kernels without BLAS. OpenBLAS is an optional *separate benchmark configuration*, not an assumed speedup: install `libopenblas-dev`, build a different directory with `-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS`, measure the real multi-image workload, then freeze one build before piloting. Do not switch builds midway through runs. See the [pinned build instructions](https://github.com/ggml-org/llama.cpp/blob/8642541b255bfb5dc39cd351a178be09013a55d6/docs/build.md).

With Docker already installed and authorized on Ubuntu, build and test the Hachi application:

```bash
cd "$HACHI_REPO"
docker build -t hachi-experiment .
docker run --rm hachi-experiment
docker image inspect hachi-experiment --format '{{.Id}}' > "$HACHI_STATE/hachi-image-id.txt"
```

This builds the application plus CPU DiffVG; it does not install Qwen or perform inference. If Docker is not installed, arrange its supported Ubuntu installation separately. Do not reuse a mismatched Python 3.10 host environment; the supplied image contains the project's Python 3.12 environment.

## 4. Download only the approved candidate files and verify bytes

The public pinned files require no Hugging Face token. Do not insert credentials into URLs. If the hosting policy changes, stop and resolve access through supported account configuration. On dot, the currently restricted network does not permit these model hosts; do not use another route to bypass that policy. These commands target the separately authorized Ubuntu machine.

```bash
cd "$HACHI_MODELS"
base='https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/resolve/1cd86afb9a95c410a6038ab3b40d8b578c892266'
# Fresh destination only; retain any interrupted .part file for diagnosis.
test ! -e Qwen3VL-4B-Instruct-Q4_K_M.gguf
test ! -e Qwen3VL-4B-Instruct-Q4_K_M.gguf.part
test ! -e mmproj-Qwen3VL-4B-Instruct-F16.gguf
test ! -e mmproj-Qwen3VL-4B-Instruct-F16.gguf.part
curl --fail --location --proto '=https' --proto-redir '=https' \
  "$base/Qwen3VL-4B-Instruct-Q4_K_M.gguf" -o Qwen3VL-4B-Instruct-Q4_K_M.gguf.part
curl --fail --location --proto '=https' --proto-redir '=https' \
  "$base/mmproj-Qwen3VL-4B-Instruct-F16.gguf" -o mmproj-Qwen3VL-4B-Instruct-F16.gguf.part
printf '%s  %s\n' 66358cb18bb6b3b1b6675aa412c7a88ef01d228f481184d13668e5201c730a0a Qwen3VL-4B-Instruct-Q4_K_M.gguf.part | sha256sum -c -
printf '%s  %s\n' 256f3a43bd4205ffef48d6b92715e1e70b5b0e9aef06522584967513a9985331 mmproj-Qwen3VL-4B-Instruct-F16.gguf.part | sha256sum -c -
mv Qwen3VL-4B-Instruct-Q4_K_M.gguf.part Qwen3VL-4B-Instruct-Q4_K_M.gguf
mv mmproj-Qwen3VL-4B-Instruct-F16.gguf.part mmproj-Qwen3VL-4B-Instruct-F16.gguf
sha256sum -c "$HACHI_REPO/configs/qwen3vl4b-candidate.sha256" > "$HACHI_STATE/model-checks.txt"
```

Any checksum failure blocks startup. The candidate checksum file must be obtained from the reviewed repository revision containing this guide; do not substitute another quantization or projector without recording and approving a new configuration.

## 5. Start one authenticated, loopback-only CPU server

Create a private random key without printing it or overwriting an existing key:

```bash
python3 - <<'PY'
import os, secrets
from pathlib import Path
path = Path(os.environ['HACHI_STATE']) / 'api-key'
with path.open('x') as f:
    f.write(secrets.token_urlsafe(32) + '\n')
path.chmod(0o600)
PY
```

Set a trial context budget and thread count based on inventory. For example, 16,384 context tokens and four threads can be initial benchmark settings; they are **not frozen study values or a promise that the full demonstration fits**. Account for `2 + 2*T` images, actual image-token expansion, prompt/history and output reserve. Avoid allocating the advertised model maximum merely because 128 GB RAM is present.

In terminal A, run the server in the foreground, leaving this terminal open:

```bash
export HACHI_CONTEXT_TOKENS=16384  # provisional diagnostic setting
export HACHI_THREADS=4            # provisional diagnostic setting
export OPENBLAS_NUM_THREADS=1
/usr/bin/time -v -o "$HACHI_STATE/server.resources.txt" \
  "$HACHI_ENGINE/build-cpu/bin/llama-server" \
  --model "$HACHI_MODELS/Qwen3VL-4B-Instruct-Q4_K_M.gguf" \
  --mmproj "$HACHI_MODELS/mmproj-Qwen3VL-4B-Instruct-F16.gguf" \
  --device none --n-gpu-layers 0 --no-mmproj-offload \
  --threads "$HACHI_THREADS" --threads-batch "$HACHI_THREADS" \
  --ctx-size "$HACHI_CONTEXT_TOKENS" --parallel 1 --no-context-shift \
  --jinja --chat-template-kwargs '{"add_vision_id":false}' \
  --alias hachi-qwen3vl4b-q4km --host 127.0.0.1 --port 8080 \
  --api-key-file "$HACHI_STATE/api-key" --no-webui --log-verbosity 3 \
  > "$HACHI_STATE/server.log" 2>&1
```

These options were checked against the pinned engine source. `add_vision_id:false` avoids adding ordinal picture labels; inspect actual behavior rather than assuming the template honored it. No separator is added to production demonstrations. Keep verbosity at info (3): the pinned source's trace logging prints part of the API key. Do not enable trace/debug or shell tracing, dump request headers, or write a literal key into a command line. The application saves request bodies and response bodies, not authentication headers. Keep all logs private because they contain task content.

Inspect `ss -ltnp` and require the listener to be on `127.0.0.1:8080`, not `0.0.0.0` or a LAN address. Do not publish this port through a router. If dot-to-Ubuntu access is later requested, arrange authorized routing and authenticated HTTPS separately; no such access has been established. Do not change the listener to an open unauthenticated service.

## 6. Probe real multi-image processing before drawing episodes

In terminal B, load the key into the client's environment without printing it:

```bash
set +x
umask 077
export HACHI_DOCKER_UID="$(id -u):$(id -g)"
case "$(docker info --format '{{json .SecurityOptions}}')" in
  *rootless*) export HACHI_DOCKER_UID=0:0 ;;
esac
export HACHI_API_KEY="$(cat "$HACHI_STATE/api-key")"
cd "$HACHI_REPO"
```

For the examples below, Docker's `--network host` is used **only on the user's authorized Linux workstation** so the client can reach its loopback server. This is not a dot cloud network-policy workaround. Rootless Docker may keep host networking inside its own network namespace, so workstation loopback reachability is not guaranteed: verify health from the actual client container first. If it fails, stop and use an authorized native client or an explicitly reviewed network arrangement; do not broaden the server bind address. No ports are published. The secret is passed by environment-variable name; do not inspect/log the container environment. If host networking is unsuitable, use an authorized same-machine native client or design a private authenticated service network explicitly.

Check `/health` and `/v1/models` using a Python HTTP client that reads the environment key and sends it in a header. Record only status, returned model metadata and the exact model ID; never print headers. Require the actual response model ID to equal the frozen alias. Model metadata alone does not establish visual capability.

Prepare fixtures using the same resolution that will be frozen for the trial, for example 256 pixels during initial diagnostics:

```bash
docker run --rm --user "$HACHI_DOCKER_UID" --network host --mount "type=bind,src=$HACHI_REPO,dst=/work" \
  --workdir /work hachi-experiment \
  python scripts/prepare_vision_check.py artifacts/vision-check --model hachi-qwen3vl4b-q4km --size 256
```

Follow [MULTI_IMAGE_ACCEPTANCE.md](MULTI_IMAGE_ACCEPTANCE.md). After explicit diagnostic execution approval, submit the saved request JSON packets through `hachi.runner.API('http://127.0.0.1:8080/v1/chat/completions', backend='self_hosted', timeout_seconds=...)` from the client environment. For each approved case/repetition, save the exact request, a pending marker before submission, the raw HTTP status/body, returned model/version, elapsed seconds, usage and failure type. Use a new private output directory; never overwrite an uncertain call or retry it automatically. Keep diagnostic outputs separate from `runs/pilot` and label them **real model diagnostics on synthetic stimuli**, not human demonstrations or study results.

A concrete client loop for the initial 18 adjacent-format calls is below. It requires an **existing actual approval record** at private/diagnostic-authorization.json with approved_by_user=true, scope=adjacent-image-diagnostic, plan_sha256 equal to `hachi.design.digest` of diagnostic-plan.json, an approval_reference, and the verified server_config object (engine/model/projector hashes and launch settings). This guide does not supply or fabricate that approval. Use a new output directory per authorized attempt.

```bash
docker run --rm -i --user "$HACHI_DOCKER_UID" --network host -e HACHI_API_KEY \
  --mount "type=bind,src=$HACHI_REPO,dst=/work" --workdir /work hachi-experiment python - <<'PYTHON'
import json, time
from pathlib import Path
from hachi.runner import API, load, save_once, picture, text
from hachi.integrity import file_sha256
from scripts.prepare_vision_check import PROMPT
from hachi.design import digest
plan = load('artifacts/vision-check/diagnostic-plan.json')
auth = load('private/diagnostic-authorization.json')
if not (auth.get('approved_by_user') is True and
        auth.get('scope') == 'adjacent-image-diagnostic' and
        auth.get('plan_sha256') == digest(plan) and
        auth.get('approval_reference') and auth.get('server_config')):
    raise SystemExit('Actual matching diagnostic approval is required')
output = Path('artifacts/vision-check-real')
output.mkdir(mode=0o700, exist_ok=False)
save_once(output/'manifest.json', {'data_kind':'real_model_diagnostic',
    'stimuli':'synthetic_identity_order_controls', 'plan':plan,
    'server_config':auth['server_config'], 'approval_reference':auth['approval_reference']})
api = API('http://127.0.0.1:8080/v1/chat/completions',
          backend='self_hosted', timeout_seconds=auth['server_config']['request_timeout_seconds'])
for case in plan['cases']:
    if case['separator'] != 'adjacent':
        continue
    packet = load(Path('artifacts/vision-check')/(case['case']+'.request.json'))
    expected = {'model':plan['model'],'temperature':0,'max_tokens':256,
        'messages':[{'role':'user','content':[text(PROMPT)] +
            [picture(Path('artifacts/vision-check')/(name+'.png')) for name in case['expected_order']]}]}
    if digest(packet) != digest(expected):
        raise SystemExit('Packet differs from the approved diagnostic layout')
    for name in case['expected_order']:
        if file_sha256(Path('artifacts/vision-check')/(name+'.png')) != plan['images_sha256'][name]:
            raise SystemExit('Diagnostic image hash mismatch')
    for repeat in range(3):
        prefix = output/f"{case['case']}-{repeat}"
        save_once(str(prefix)+'.request.json', packet)
        save_once(str(prefix)+'.pending.json', {'started_at':time.time(),'request_sha256':digest(packet)})
        try:
            response = api(packet)
        except Exception as error:
            save_once(str(prefix)+'.failure.json', {'type':type(error).__name__,'outcome':'uncertain'})
            raise SystemExit('Diagnostic stopped; reconcile server outcome before any authorized retry')
        save_once(str(prefix)+'.response.json', response)
        if response['http_status'] != 200:
            raise SystemExit('HTTP failure retained; diagnostic stopped')
        if json.loads(response['body']).get('model') != plan['model']:
            raise SystemExit('Returned model mismatch retained; diagnostic stopped')
# Identity/order judgments are made from the preserved raw responses, not invented here.
PYTHON
```

Run single-image A/B controls, then AB/BA/AA/BB with at least three repetitions each (18 adjacent-format calls total), checking identity, order and duplicates rather than just image count. The optional newline diagnostic adds 18 calls if separately included in the approved scope. It does not authorize a production prompt change. Inspect the maximum-image-count production layout and late-episode history afterwards; two-image success alone is insufficient. If adjacent images fail, stop and review engine/template handling. Never silently resize one image, add ordinal labels, truncate demonstrations or change to segment guidance.

## 7. Measure real time, memory and failures

Record startup-to-ready duration separately from request latency. For each request retain end-to-end API elapsed time and provider-reported token usage; report missing token counts as missing. Record first-request and warmed-request distributions separately. Do not estimate image preprocessing from text-only token/s.

Identify the one server PID with `ps -C llama-server -o pid=,comm=` and verify `/proc/PID/exe` points to the pinned binary. If several processes exist, select the correct one explicitly. During requests, collect timestamped `VmRSS` and `VmHWM` from `/proc/PID/status`; do not read `/proc/PID/environ` or copy its command line. GNU time's server.resources.txt, finalized when the foreground server exits, gives elapsed time, maximum resident set size, CPU time and exit status. This is server memory, including the loaded model; timing the Docker client alone does not measure server memory. Note swap pressure and system load, and keep sampling frequency/configuration fixed. RSS is resident memory, not the sum of GGUF file sizes.

For example, after setting HACHI_SERVER_PID to the verified server PID, this read-only sampler writes epoch time and resident/high-water memory in Linux kB. Run it in a separate terminal and stop it with Ctrl+C; it does not read credentials or process arguments.

```bash
export HACHI_SERVER_PID=VERIFIED_NUMERIC_PID
python3 - <<'PYTHON' > "$HACHI_STATE/server-memory.csv"
import csv, os, sys, time
from pathlib import Path
pid = int(os.environ['HACHI_SERVER_PID'])
writer = csv.writer(sys.stdout)
writer.writerow(['epoch_seconds','rss_kb','high_water_kb'])
try:
    while True:
        try:
            lines = Path(f'/proc/{pid}/status').read_text().splitlines()
        except FileNotFoundError:
            break
        fields = {line.split(':',1)[0]:line.split(':',1)[1].strip()
                  for line in lines if line.startswith(('VmRSS:','VmHWM:'))}
        writer.writerow([time.time(),fields.get('VmRSS','').split(' ')[0],
                          fields.get('VmHWM','').split(' ')[0]])
        sys.stdout.flush()
        time.sleep(1)
except KeyboardInterrupt:
    pass
PYTHON
```

Failures must be counted and retained: startup errors, unsupported flags, incorrect model/projector, HTTP errors, authentication failures, context overflow, image omissions/order errors, invalid JSON/actions, client timeouts, process exits and memory exhaustion. Record the command/request index and whether an outcome is known or uncertain. Do not delete failed attempts to improve reported success or latency. If a timeout might have completed on the server, inspect its logs before any authorized retry; the drawing runner already blocks automatic uncertain retries.

## 8. Freeze and run only the authorized development pilot

After technical model acceptance, freeze the exact model/engine/binary hashes, quantization, chat template and template kwargs, context/image settings, decoding, thread count, output/history limits, timeout, pen width and rubric version. Put the actual alias in protocol.model and the confirmed weight/projector hashes, engine version and Q4_K_M quantization in the existing self-hosted protocol fields. `context_limit_tokens` records a limit; actual processor/server behavior still needs measurement. A context/output truncation failure is not successful full-context guidance.

Obtain real human target/demonstration materials and complete both sets in the shared registry. Freeze all materials and plan only development tasks:

```bash
hachi freeze-materials materials/development.json materials/evaluation.json private/materials.json
hachi plan materials/development.json private/pilot-plan.json --stage pilot --repeats 1 --seed 20261104
```

These are Hachi CLI commands; on the Docker workstation run them with `docker run --rm --user "$HACHI_DOCKER_UID" --mount "type=bind,src=$HACHI_REPO,dst=/work" --workdir /work --entrypoint hachi hachi-experiment ...`. Choose an explicitly recorded small development subset for initial pilot scope if all six development targets would be excessive; do not use evaluation targets. The complete shared registry must still include both sets.

Authorization must record an actual user approval, stage `pilot`, plan/protocol hashes, materials_sha256, approval_reference and local_model_execution_approved. Do not generate a fictitious approval. Then use:

```bash
docker run --rm --user "$HACHI_DOCKER_UID" --network host -e HACHI_API_KEY \
  --mount "type=bind,src=$HACHI_REPO,dst=/work" --workdir /work \
  --entrypoint hachi hachi-experiment \
  run private/pilot-plan.json materials/development.json configs/protocol.json \
  private/pilot-authorization.json runs/pilot \
  --materials-manifest private/materials.json --backend self_hosted \
  --endpoint http://127.0.0.1:8080/v1/chat/completions
```

The three conditions and 40-command cap remain unchanged. Logs, state images and provenance are retained. Resume only with unchanged code, renderer, model source, protocol and materials. Prepare blind materials for actual human ratings; do not infer study completion from a successful API call or invented labels.

Report pilot success/failures, real command counts, invalid actions, full-context coverage, latency distribution, peak RSS, elapsed campaign time and missing measurements. Estimate 54-run duration from measured condition-specific episode times, including rendering/logging overhead, and disclose uncertainty. At most 2,160 action calls are possible for 54 runs before separately authorized retries; no actual duration is known yet. Self-hosting has no external per-token API charge but consumes the owner's hardware, electricity and time. Stop after the pilot report; the 54-run stage needs a separate user decision and approval.

## 9. Stop and clean up without losing evidence

Stop the foreground server with Ctrl+C; let GNU time finish writing resources. If needed, send SIGINT to the verified server PID only, then confirm it exited and the loopback port closed. Do not use broad `pkill` patterns. Stop a known remaining client container by its recorded container ID; do not stop unrelated containers. Unset `HACHI_API_KEY` in client shells.

Archive the approved configuration, hashes, raw requests/responses, server diagnostics, resource measurements, failures and human-review materials in a private location. Exclude the api-key file. If credentials may have appeared in a trace, stop, rotate the key, and retain only redacted diagnostics for sharing; do not publish the compromised trace.

Only after checking that no run or server needs them, delete task-specific interrupted `.part` downloads or a chosen build directory. Model files can be retained for reproducibility or removed by exact filename after approval. Keep successful raw runs and failures; do not erase evidence as cleanup. Delete/revoke the private API key when this deployment is retired. Avoid broad Docker system prune commands that could remove unrelated work.
