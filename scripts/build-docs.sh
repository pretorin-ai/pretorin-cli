#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

mdbook build docs
cp docs/llms.txt docs/book/llms.txt
cp docs/llms-full.txt docs/book/llms-full.txt
