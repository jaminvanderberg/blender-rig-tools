#!/usr/bin/env bash
set -u

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SRC="${ROOT}/rigtools"
OUT="${ROOT}/rigtools.zip"

if [[ ! -f "${SRC}/__init__.py" ]]; then
  echo "ERROR: ${SRC}/__init__.py not found."
  exit 1
fi

rm -f "${OUT}"

if command -v zip >/dev/null 2>&1; then
  (cd "${ROOT}" && zip -qr "${OUT}" rigtools)
else
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: zip or python3 is required to build the archive."
    exit 1
  fi

  python3 - "$SRC" "$OUT" <<'PY'
import os
import sys
import zipfile

src = sys.argv[1]
out = sys.argv[2]

base_dir = os.path.dirname(src)

with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(src):
        for name in files:
            full_path = os.path.join(root, name)
            arcname = os.path.relpath(full_path, base_dir)
            zf.write(full_path, arcname)
PY
fi

if [[ $? -ne 0 ]]; then
  echo "ERROR: Failed to create zip."
  exit 1
fi

echo "Created: ${OUT}"
exit 0
