#!/bin/sh
set -eu
unset DOCKER_HOST DOCKER_CONTEXT DOCKER_TLS DOCKER_TLS_VERIFY DOCKER_CERT_PATH
# Arguments are the same as the hachi CLI. Auth is inherited, never printed.
if [ -n "${CODEX_PROXY_CERT:-}" ]; then
  docker --host=unix:///var/run/docker.sock run --rm --user "$(id -u):$(id -g)" \
    --mount "type=bind,src=$PWD,dst=/work" --workdir /work \
    --mount type=bind,src=/etc/ssl/certs/ca-certificates.crt,dst=/run/proxy-ca.pem,readonly \
    -e REQUESTS_CA_BUNDLE=/run/proxy-ca.pem -e HACHI_API_KEY \
    --entrypoint hachi hachi-experiment "$@"
else
  docker --host=unix:///var/run/docker.sock run --rm --user "$(id -u):$(id -g)" \
    --mount "type=bind,src=$PWD,dst=/work" --workdir /work -e HACHI_API_KEY \
    --entrypoint hachi hachi-experiment "$@"
fi
