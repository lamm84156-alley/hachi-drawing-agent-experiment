#!/bin/sh
set -eu
unset DOCKER_HOST DOCKER_CONTEXT DOCKER_TLS DOCKER_TLS_VERIFY DOCKER_CERT_PATH
if [ -n "${CODEX_PROXY_CERT:-}" ]; then
  docker --host=unix:///var/run/docker.sock build --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt -t hachi-experiment .
else
  docker --host=unix:///var/run/docker.sock build -t hachi-experiment .
fi
docker --host=unix:///var/run/docker.sock run --rm hachi-experiment
