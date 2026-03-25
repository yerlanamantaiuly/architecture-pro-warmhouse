#!/usr/bin/env bash

set -euo pipefail

if [[ -z "${APP_DOMAIN:-}" ]]; then
  echo "APP_DOMAIN is required"
  exit 1
fi

if [[ -z "${APP_REDIRECT_DOMAIN:-}" ]]; then
  echo "APP_REDIRECT_DOMAIN is required"
  exit 1
fi

for attempt in $(seq 1 12); do
  if curl --fail --silent --show-error "https://${APP_DOMAIN}/health" >/dev/null \
    && curl --fail --silent --show-error "https://${APP_DOMAIN}/api/v1/sensors" >/dev/null \
    && curl --fail --silent --show-error --location "https://${APP_REDIRECT_DOMAIN}/health" >/dev/null; then
    echo "Smoke checks passed on attempt ${attempt}"
    exit 0
  fi

  echo "Smoke checks not ready yet, attempt ${attempt}/12"
  sleep 5
done

echo "Smoke checks failed after all retries"
exit 1
