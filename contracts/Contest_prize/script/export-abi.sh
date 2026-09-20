#!/usr/bin/env bash
# Regenerates the ContestPrize ABI used by the backend and the frontend.
# Run it after every change to src/ContestPrize.sol and commit the generated files.
#   bash script/export-abi.sh
set -euo pipefail
cd "$(dirname "$0")/.."

FORGE="${FORGE:-forge}"
BACKEND_ABI="../../backend/contractapi/abi/ContestPrize.json"
FRONTEND_ABI="../../frontend/src/blockchain/ContestPrize.abi.json"

"$FORGE" build --silent
"$FORGE" inspect ContestPrize abi --json > "$BACKEND_ABI"
cp "$BACKEND_ABI" "$FRONTEND_ABI"
echo "ABI written to $BACKEND_ABI and $FRONTEND_ABI"
