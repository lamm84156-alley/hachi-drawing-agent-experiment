# Real-model image identity/order acceptance (not yet run)

Current adapter audit: every demonstration transition is `[before image, action JSON text, after image]`. Between consecutive transitions, the preceding after-image and the next before-image are adjacent image blocks. The target image is also adjacent to the first demonstration before-image. They have the same frozen resolution. No automatic text separator, image resizing, omitted frame, or video conversion has been added.

The upstream reports are version-specific evidence of a risk, not proof that the chosen future deployment is affected. llama.cpp issue 24303 describes Qwen3.6-35B-A3B on b9553 merging adjacent images; a later commenter reports a fix with b10485. Ollama issue 17321 describes 0.32.0/0.32.1 with pinned llama.cpp b9888 and same-sized images through its native /api/chat endpoint. Our adapter uses Chat Completions; behavior must be tested on its exact endpoint, engine, template, weights and projector. Sources: https://github.com/ggml-org/llama.cpp/issues/24303 and https://github.com/ollama/ollama/issues/17321 (reviewed 2026-11-04).

## Preparation without inference

`python scripts/prepare_vision_check.py artifacts/vision-check --model FROZEN_MODEL_ID --size FROZEN_RESOLUTION`

This creates two same-sized black-on-white technical images: a circle in the upper left and a triangle in the lower right. It writes A, B, AB, BA, AA and BB diagnostic request packets and a separate expected-identity manifest. There are no ordinal image labels or shape names embedded in the requests. These generated fixtures are not human demonstrations or research observations. The command makes zero API calls and records status not_run.

Both adjacent-image and neutral-newline diagnostic variants are prepared. The second variant is a diagnostic candidate only; it does not change production prompts. A whitespace separator might be stripped by the server, so its mere presence is not evidence of a fix.

## Actual acceptance after model/deployment or spending approval

1. Freeze engine commit/build, chat template, model/projector hashes, quantization, processor options, resolution, decoding and seed support. Run at least three repetitions per diagnostic case per variant; retain every result, not only successful examples. Do not send the expected-identity manifest to the model.
2. Submit the actual image-bearing packets to the real endpoint. Save exact requests and raw responses, timestamps, returned model ID, usage, engine logs and configuration. Mark actual provenance; a mock transport result cannot satisfy this check.
3. First require that single-image A and B identify the visible shapes and positions. Then check AB and BA recover both identities in the correct sequence, and AA/BB retain two entries despite duplicate content. An image-count answer alone is insufficient. Record wrong identities, omissions, swaps, refusals and malformed JSON separately. Require all fixed diagnostic cases/repetitions to pass before progressing; this is an engineering gate, not a scientific completion metric.
4. Inspect server preprocessing diagnostics where available: media markers, decoded images and any temporal-merge behavior. Do not infer correctness solely from raw token count, as image-tokenization varies. If internal image handling cannot be inspected, document that limitation and rely on behavioral checks without claiming the merger was directly observed.
5. Repeat with the actual production content layout (including adjacent transition boundaries), then the maximum `2+2*T` image count and late-episode history on development-only materials. Verify coverage of every image and order, actual context fit, CPU latency and peak RAM. Two-image success alone does not establish full-context suitability.
6. If adjacent inputs fail but a neutral separator passes, stop before study runs. Record the exact proposed separator and template/processor behavior for protocol review. Use one uniform nonsemantic separator, without ordinal labels, part names, timestamps, demonstrations selected by retrieval, or altered image resolution. It must be frozen consistently across Original/Reordered; No Demo still omits demonstrations. Any context-driven switch to segment guidance requires the Proposal's explicit declaration before evaluation. Do not silently introduce a workaround.

No target engine/model has been deployed or tested here. The reported upstream issue is not claimed to reproduce on the eventual target version. No local-model download, paid inference, or formal evaluation is authorized by this acceptance document.
