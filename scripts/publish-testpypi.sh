#!/usr/bin/env bash
set -euo pipefail

ORIG_NAME="azure-doc-processing"
TEST_NAME="azure-doc-processing-test"

echo ">>> Step 0: Clean previous build artifacts"
rm -rf dist build ./*.egg-info

echo ">>> Step 1: Modify pyproject.toml to use test package name"
cp pyproject.toml pyproject.toml.bak

# Replace the package name
sed -i "s/name = \"$ORIG_NAME\"/name = \"$TEST_NAME\"/" pyproject.toml

echo ">>> Step 2: Build distributions"
poetry build

echo ">>> Step 3: Check distributions"
twine check dist/*

echo ">>> Step 4: Upload to TestPyPI"
twine upload --repository testpypi dist/*

echo ">>> Step 5: Restore original pyproject.toml"
mv pyproject.toml.bak pyproject.toml

echo ">>> Step 6: Create temporary virtualenv"
TMPDIR=$(mktemp -d)
python -m venv "$TMPDIR/venv"
source "$TMPDIR/venv/bin/activate"

echo ">>> Step 7: Install from TestPyPI"
pip install --upgrade pip
pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple \
  "$TEST_NAME"

echo ">>> Step 8: Smoke test"
python - << 'PYCODE'
import importlib.metadata as m

dist_name = "azure-doc-processing-test"
print("Installed version:", m.version(dist_name))

import azure_doc_processing as pkg
print("Imported module path:", pkg.__file__)
PYCODE

echo ">>> All good 🚀 (published as $TEST_NAME)"
