#!/usr/bin/env bash

set -euo pipefail

if [[ -z "${MVP_APP_DOMAIN:-}" ]]; then
  echo "MVP_APP_DOMAIN is required"
  exit 1
fi

for attempt in $(seq 1 12); do
  if curl --fail --silent --show-error "https://${MVP_APP_DOMAIN}/health" >/dev/null \
    && curl --fail --silent --show-error "https://${MVP_APP_DOMAIN}/devices/health" >/dev/null \
    && curl --fail --silent --show-error "https://${MVP_APP_DOMAIN}/telemetry/health" >/dev/null; then
    echo "MVP smoke checks passed on attempt ${attempt}"
    exit 0
  fi

  echo "MVP smoke checks not ready yet, attempt ${attempt}/12"
  sleep 5
done

echo "MVP smoke checks failed after all retries"
exit 1
