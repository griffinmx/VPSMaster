#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v python3 >/dev/null 2>&1; then
  echo '需要 Python 3.10+ / Python 3.10+ is required.' >&2
  exit 2
fi
if [ "$#" -eq 0 ]; then
  exec python3 -u -m proxydoctor suite
fi
exec python3 -u -m proxydoctor "$@"
