#!/bin/bash
set -e

cd "$(dirname "$0")"
uv run --directory opencode_python ty check --output-format concise "$@"
