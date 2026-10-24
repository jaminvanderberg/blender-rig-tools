#!/usr/bin/env bash
set -u

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV="${ROOT}/.venv"

if [[ ! -x "${VENV}/bin/python" ]]; then
  if ! python3 -m venv "${VENV}"; then
    echo "ERROR: Failed to create .venv. Is python3 installed? (Debian/Ubuntu: sudo apt install python3-venv)"
    exit 1
  fi
fi

if ! "${VENV}/bin/pip" install --upgrade -r "${ROOT}/requirements-dev.txt"; then
  echo "ERROR: Failed to install requirements."
  exit 1
fi

echo "Dev environment ready. Reload VS Code."
exit 0
