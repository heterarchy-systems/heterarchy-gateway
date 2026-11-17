#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
    printf 'Usage: %s <image-reference>\n' "$0" >&2
    exit 2
fi

image=$1
container="gateway-image-smoke-${GITHUB_RUN_ID:-local}-$$"
trap 'docker rm --force "$container" >/dev/null 2>&1 || true' EXIT

docker run --detach --platform linux/amd64 --name "$container" \
    --env GATEWAY_FORGE_BASE_URL=http://127.0.0.1:8797/api/v1 \
    --env GATEWAY_ORCHESTRATION_BASE_URL=http://127.0.0.1:8798 \
    --env GATEWAY_FAILURE_SIMULATION_ENABLED=false \
    --env GATEWAY_HTTP_TIMEOUT_SECONDS=10.0 \
    --env GATEWAY_MAX_CONNECTIONS=100 \
    --env GATEWAY_MAX_KEEPALIVE_CONNECTIONS=20 \
    --env GATEWAY_TRACE_CAPACITY=500 \
    --env GATEWAY_HOST=127.0.0.1 \
    --env GATEWAY_PORT=7979 \
    "$image"

for attempt in {1..30}; do
    health=$(docker inspect --format '{{.State.Health.Status}}' "$container")
    if [[ "$health" == healthy ]]; then
        docker exec "$container" /usr/local/bin/uv run --locked --no-sync --python 3.14.7t \
            python -c 'import sys; assert sys.version_info[:3] == (3, 14, 7); assert not sys._is_gil_enabled()'
        printf 'Gateway image runtime and /healthz verified.\n'
        exit 0
    fi
    state=$(docker inspect --format '{{.State.Status}}' "$container")
    if [[ "$state" != running ]]; then
        break
    fi
    sleep 2
done

docker logs "$container" >&2
printf 'Gateway image health check failed.\n' >&2
exit 1
