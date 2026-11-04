# VLM inside the dot cloud environment

This means serving weights in this cloud worker, not on the user's computer. The experiment adapter accepts an OpenAI-compatible Chat Completions endpoint at `http://127.0.0.1:PORT/v1/chat/completions` without an API key, or HTTPS for remote APIs. Loopback refers to the calling process/container; run the model and experiment in the same container or configure an authorized HTTPS service endpoint. No model is downloaded or started by this repository.

Observed 2026-11-04: Docker local daemon works; no /dev/nvidia* or /dev/dri devices exposed. Installed PyTorch is CPU-only, CUDA unavailable. OS reports five logical CPUs and 17.59 GiB total memory, but cgroup limits are the effective constraint: memory.max = 17179869184 (16 GiB), cpu.max = 400000/100000 (4 CPU equivalents). Workspace overlay is 32 GB; about 21 GB was free after compact-image recovery and final-source packaging. Free disk is shared with dependencies, Docker layers and logs. These observations do not establish GPU support.

Network policy is restricted and enforced. Package registries and GitHub are allowed, but Hugging Face/model-weight CDN hosts and provider API domains are not in the configured allowlist. Loading weights would need an approved configuration update for the actual download hosts, or authorized local weight files. Do not route around the proxy. No model credentials are configured. Environment lifetime, idle shutdown and maximum job duration are not exposed by the inspected runtime status; uninterrupted multi-hour execution and persistence after teardown are unverified.

A small quantized multimodal model with a CPU-capable runtime is a plausible candidate under 16 GiB, not a verified performance result. Weight-only arithmetic for 4 billion parameters is about 8 GB at 16-bit or 2 GB at 4-bit, excluding projector, quantization metadata, KV cache, vision activations and runtime. Full-context image sequences can dominate memory and latency. No tokens/s, end-to-end latency or maximum feasible context has been measured. A larger GPU allocation would require separate environment configuration and cost approval.

Official llama.cpp documentation describes CPU inference, multimodal OpenAI-compatible serving and an explicit `--no-mmproj-offload` mode. vLLM documents multimodal Chat Completions and configurable image-per-prompt limits. These establish an integration route, not that any chosen model works on this worker:

- https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md
- https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- https://docs.vllm.ai/en/stable/features/multimodal_inputs/

Proposal-preserving acceptance criteria after choosing and authorizing a model:

1. Pin model weights/revision, multimodal projector hash, quantization, inference engine version, chat template and all decoding/image settings. Use one fixed model across all conditions. Quantization becomes part of that fixed model configuration.
2. Send target + current canvas + both images for every demonstration transition: `2 + 2*T` images for T paths; No Demo has two. Do not collapse before/after frames, silently reduce context, use semantic step labels, or switch to segment guidance. Configure server multimodal limit accordingly.
3. Measure actual processor/tokenizer image-token expansion and full prompt/output fit against the frozen context. Server-reported capacity alone is insufficient. Context failures halt; they do not trigger truncation.
4. Verify real images affect real output and the server actually processes every image, then run complete real development episodes in all three conditions. Validate strict JSON actions with the existing parser; malformed JSON still consumes a command. Schema-constrained decoding, if selected, must be fixed across conditions before pilot.
5. Measure peak RSS, total duration, tokens, command failure rate and model version. CPU performance must be demonstrated before estimating 54-run duration. Preserve all request/response bytes and failure records.

Local execution has no per-token external API fee, but compute/storage and any cloud resource upgrades may have costs. No cost-free infrastructure assumption is made. Local authorization uses `local_model_execution_approved` instead of `api_spending_approved`, and requires protocol fields `weights_sha256`, `projector_sha256`, `inference_engine_version`, `quantization`. The user has asked about feasibility only; no local deployment or formal run is authorized yet.

## Separate Ubuntu CPU workstation (user-reported, not inspected)

The user also has an Ubuntu machine with 128 GB RAM, no GPU, and a possibly ninth-generation Intel i9. Exact CPU model, core count, instruction support, free RAM/disk, and throughput remain unverified. Do not infer AVX capabilities or a performance number from that description. More memory can accommodate larger weights/context, but CPU memory bandwidth and compute still limit latency. Start with the same small multimodal candidate and measure, rather than selecting a large model solely because it fits in RAM.

After the owner authorizes setup, record `lscpu`, `free -h`, `df -h`, Ubuntu version, engine build flags/version, model/projector hashes and quantization. Benchmark a complete full-context request at the longest demonstration length and late-episode history, then a complete three-condition development pilot. Record cold/warm latency, peak RSS, tokens/sec when reported, image count, context usage, structured-action validity and episode duration. Do not substitute a text-only benchmark or one-image test for this workload. The `request_timeout_seconds` protocol field can extend the default 120 seconds for CPU inference; freeze it before runs.

Two supported arrangements, neither connected or authorized yet:

- Run this repository and the model server together on Ubuntu, using loopback. Copy reviewed results back afterwards. No inbound access from the cloud is needed.
- Run the experiment in dot and a self-hosted model endpoint on Ubuntu using `--backend self_hosted --endpoint https://AUTHORIZED_HOST/v1/chat/completions`. Non-loopback endpoints require HTTPS and HACHI_API_KEY authentication. Establish approved VPN/network routing and server-side authentication first; localhost in dot does not reach the Ubuntu machine. No network access to that computer has been attempted.

Both use the same image-bearing requests, action validator, 40-command budget and logs. `self_hosted` uses local-model execution approval and frozen weight/projector/engine metadata rather than external token-spending approval. Do not expose an unauthenticated inference server to the public Internet. No assumption is made that the machine is reachable or that installation is approved.

See [MULTI_IMAGE_ACCEPTANCE.md](MULTI_IMAGE_ACCEPTANCE.md) for the version-specific adjacent-image risk audit and a real-model two-image identity/order gate. The production adapter remains unchanged with respect to image separators. Model source and endpoint are now frozen per run and per response; changing transport during resume is prohibited, including switching a technical fixture to an API object.
