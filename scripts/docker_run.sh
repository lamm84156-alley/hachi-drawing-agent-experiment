#!/bin/sh
set -eu
unset DOCKER_HOST DOCKER_CONTEXT DOCKER_TLS DOCKER_TLS_VERIFY DOCKER_CERT_PATH
docker_run_uid="$(id -u):$(id -g)"
# Root in a rootless daemon maps to the invoking host user; numeric host IDs
# inside that namespace would refer to subordinate users and lose bind access.
if docker --host=unix:///var/run/docker.sock info --format '{{json .SecurityOptions}}' | grep -q rootless; then
  docker_run_uid=0:0
fi
# Arguments are the same as the hachi CLI. Auth is inherited, never printed.
if [ -n "${CODEX_PROXY_CERT:-}" ]; then
  docker --host=unix:///var/run/docker.sock run --rm --user "$docker_run_uid" \
    --mount "type=bind,src=$PWD,dst=/work" --workdir /work \
    --mount type=bind,src=/etc/ssl/certs/ca-certificates.crt,dst=/run/proxy-ca.pem,readonly \
    -e REQUESTS_CA_BUNDLE=/run/proxy-ca.pem -e HACHI_API_KEY \
    --entrypoint hachi hachi-experiment "$@"
else
  docker --host=unix:///var/run/docker.sock run --rm --user "$docker_run_uid" \
    --mount "type=bind,src=$PWD,dst=/work" --workdir /work -e HACHI_API_KEY \
    --entrypoint hachi hachi-experiment "$@"
fi
