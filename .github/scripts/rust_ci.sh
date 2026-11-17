#!/usr/bin/env bash
set -euo pipefail

usage() {
    printf 'Usage: GATEWAY_LIVE_RUST_BUILD_ROOT=/absolute/path %s <forge|orchestration> <command> [args...]\n' "$0" >&2
    exit 2
}

if (( $# < 2 )); then
    usage
fi

category=$1
shift

case "$category" in
    forge|orchestration)
        ;;
    *)
        usage
        ;;
esac

build_root=${GATEWAY_LIVE_RUST_BUILD_ROOT:-}
if [[ -z "$build_root" ]]; then
    printf 'GATEWAY_LIVE_RUST_BUILD_ROOT is required.\n' >&2
    exit 2
fi
if [[ "$build_root" != /* ]]; then
    printf 'GATEWAY_LIVE_RUST_BUILD_ROOT must be an absolute path.\n' >&2
    exit 2
fi

cargo_home="$build_root/cargo-home"
cargo_target="$build_root/$category"
temporary_root="$build_root/tmp"
mkdir -p "$cargo_home" "$cargo_target" "$temporary_root"

export CARGO_HOME="$cargo_home"
export CARGO_TARGET_DIR="$cargo_target"
export TMPDIR="$temporary_root"
export CARGO_INCREMENTAL=0
export CARGO_PROFILE_DEV_DEBUG=0
export CARGO_PROFILE_TEST_DEBUG=0

exec "$@"
