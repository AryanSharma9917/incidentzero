#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KIND_BIN="${KIND_BIN:-kind}"
KUBECTL_BIN="${KUBECTL_BIN:-kubectl}"
CLUSTER_NAME="${CLUSTER_NAME:-incidentzero}"
IMAGE="incidentzero/payment-api:local"

if ! "$KIND_BIN" get clusters | grep -Fxq "$CLUSTER_NAME"; then
  "$KIND_BIN" create cluster --config "$ROOT_DIR/sandbox/kind-config.yaml"
fi

docker build --tag "$IMAGE" "$ROOT_DIR/sandbox/base/app"
"$KIND_BIN" load docker-image "$IMAGE" --name "$CLUSTER_NAME"
"$KUBECTL_BIN" apply -k "$ROOT_DIR/sandbox/base"
"$KUBECTL_BIN" rollout restart deployment/payment-api --namespace incidentzero-demo
"$KUBECTL_BIN" rollout status deployment/payment-api \
  --namespace incidentzero-demo --timeout=90s
"$KUBECTL_BIN" get pods --namespace incidentzero-demo
