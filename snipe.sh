#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Ensure setup has been run
if [ ! -f "${SCRIPT_DIR}/config.json" ] || [ ! -f "${SCRIPT_DIR}/oci_config" ]; then
    echo ""
    echo "  Setup has not been completed yet."
    echo "  Run ./setup.sh first, then try again."
    echo ""
    exit 1
fi

# Activate the virtual environment
if [ ! -d "${SCRIPT_DIR}/.venv" ]; then
    echo ""
    echo "  Python environment not found."
    echo "  Run ./setup.sh first, then try again."
    echo ""
    exit 1
fi

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/.venv/bin/activate"

exec python3 "${SCRIPT_DIR}/sniper.py" "$@"
