#!/usr/bin/env bash
set -euo pipefail

PACKAGE_NAME="azure-doc-processing"

echo ">>> Step 0: Clean previous build artifacts"
rm -rf dist build ./*.egg-info

echo ">>> Step 1: Build distributions with Poetry"
poetry build

echo ">>> Step 2: Check distributions with twine"
twine check dist/*

echo ">>> Step 3: Upload to PyPI (production)"
# Uses ~/.pypirc [pypi] section or TWINE_USERNAME/TWINE_PASSWORD env vars
twine upload dist/*

echo ">>> Step 4: Create temporary virtualenv"
TMPDIR=$(mktemp -d)
python -m venv "$TMPDIR/venv"
# shellcheck source=/dev/null
source "$TMPDIR/venv/bin/activate"

echo ">>> Step 5: Install from REAL PyPI"
pip install --upgrade pip
pip install "${PACKAGE_NAME}"

echo ">>> Step 6: Smoke-test import"
python - << 'PYCODE'
import importlib.metadata as m

dist_name = "azure-doc-processing"
print("Installed version from PyPI:", m.version(dist_name))

import azure_doc_processing as pkg
print("Imported module path:", getattr(pkg, "__file__", "unknown"))
PYCODE

echo ">>> All good ✅ Package successfully published & installable from PyPI"
