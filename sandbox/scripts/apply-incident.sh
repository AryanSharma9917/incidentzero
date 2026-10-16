#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KUBECTL_BIN="${KUBECTL_BIN:-kubectl}"
SCENARIO="${1:-}"

case "$SCENARIO" in
  oomkilled|crashloop|readiness) ;;
  *)
    echo "usage: $0 {oomkilled|crashloop|readiness}" >&2
    exit 2
    ;;
esac

"$KUBECTL_BIN" apply -k "$ROOT_DIR/sandbox/incidents/$SCENARIO"
"$KUBECTL_BIN" rollout restart deployment/payment-api --namespace incidentzero-demo
echo "Applied '$SCENARIO'. Observe with: $KUBECTL_BIN get pods -n incidentzero-demo -w"
