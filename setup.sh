#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

hr() { printf '\n  %-60s\n\n' "──────────────────────────────────────────────────────"; }

step() { printf '\n  \033[1;34m[%s]\033[0m  %s\n' "$1" "$2"; }

ok()   { printf '  \033[1;32m✓\033[0m  %s\n' "$1"; }

err()  { printf '\n  \033[1;31m✗\033[0m  %s\n\n' "$1" >&2; }

prompt() {
    # prompt <var_name> <question> [default]
    local _var="$1"
    local _q="$2"
    local _default="${3:-}"
    local _input

    if [ -n "$_default" ]; then
        printf '  %s [%s]: ' "$_q" "$_default"
    else
        printf '  %s: ' "$_q"
    fi
    read -r _input
    if [ -z "$_input" ] && [ -n "$_default" ]; then
        _input="$_default"
    fi
    # Assign to the named variable (bash 3.2 compatible)
    eval "${_var}=\$_input"
}

validate_ocid() {
    local ocid="$1"
    case "$ocid" in
        ocid1.*) return 0 ;;
        *) return 1 ;;
    esac
}

# ─────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────

clear
printf '\n'
printf '  \033[1;37m Oracle Cloud A1.Flex VM — One-time Setup\033[0m\n'
printf '  Polls for ARM capacity and creates your VM when a slot opens.\n'
hr

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Check Python 3
# ─────────────────────────────────────────────────────────────────────────────

step "1/9" "Checking for Python 3"

if ! command -v python3 >/dev/null 2>&1; then
    err "python3 not found."
    printf '  macOS ships Python 3 only when Xcode Command Line Tools are installed.\n'
    printf '  Run this in Terminal, accept the prompt, wait for it to finish,\n'
    printf '  then re-run ./setup.sh:\n\n'
    printf '      xcode-select --install\n\n'
    exit 1
fi

PYTHON_VERSION="$(python3 --version 2>&1)"
ok "Found $PYTHON_VERSION"

# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Create virtual environment + install deps
# ─────────────────────────────────────────────────────────────────────────────

step "2/9" "Setting up Python environment"

if [ ! -d "${SCRIPT_DIR}/.venv" ]; then
    python3 -m venv "${SCRIPT_DIR}/.venv"
fi

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/.venv/bin/activate"

printf '  Installing dependencies (oci, requests)...\n'
pip install -q -r "${SCRIPT_DIR}/requirements.txt"

ok "Dependencies installed"

# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Collect Oracle OCIDs
# ─────────────────────────────────────────────────────────────────────────────

step "3/9" "Oracle Cloud credentials"

printf '\n'
printf '  You need two OCIDs from the Oracle Console.\n'
printf '  See docs/oracle-signup-guide.md for where to find them.\n'
hr

TENANCY_OCID=""
while [ -z "$TENANCY_OCID" ]; do
    prompt TENANCY_OCID "Tenancy OCID (starts with ocid1.tenancy...)"
    if ! validate_ocid "$TENANCY_OCID"; then
        err "That doesn't look like an OCID (should start with ocid1.). Try again."
        TENANCY_OCID=""
    fi
done

USER_OCID=""
while [ -z "$USER_OCID" ]; do
    prompt USER_OCID "User OCID (starts with ocid1.user...)"
    if ! validate_ocid "$USER_OCID"; then
        err "That doesn't look like an OCID (should start with ocid1.). Try again."
        USER_OCID=""
    fi
done

prompt REGION "Region (e.g. us-ashburn-1, us-phoenix-1, eu-frankfurt-1)" "us-ashburn-1"

# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Generate OCI API signing key
# ─────────────────────────────────────────────────────────────────────────────

step "4/9" "Generating OCI API signing key"

OCI_KEY="${SCRIPT_DIR}/oci_api_key.pem"
OCI_KEY_PUB="${SCRIPT_DIR}/oci_api_key_public.pem"

if [ ! -f "$OCI_KEY" ]; then
    openssl genrsa -out "$OCI_KEY" 2048 2>/dev/null
    chmod 600 "$OCI_KEY"
fi
openssl rsa -pubout -in "$OCI_KEY" -out "$OCI_KEY_PUB" 2>/dev/null

FINGERPRINT="$(openssl rsa -pubout -outform DER -in "$OCI_KEY" 2>/dev/null \
    | openssl md5 -c \
    | awk '{print $2}')"

ok "Key generated. Fingerprint: $FINGERPRINT"

# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Upload public key to Oracle Console
# ─────────────────────────────────────────────────────────────────────────────

step "5/9" "Add the API key to Oracle Console"

printf '\n'
printf '  1. Open Oracle Console → top-right avatar → My Profile\n'
printf '  2. Scroll down → "API Keys" → "Add API Key"\n'
printf '  3. Choose "Paste a Public Key" and paste the key below:\n'
hr
cat "$OCI_KEY_PUB"
hr
printf '  4. Click Add. Oracle will confirm with the fingerprint:\n'
printf '     \033[1;33m%s\033[0m\n' "$FINGERPRINT"
printf '  5. If it matches, press Enter here to continue.\n\n'
printf '  Press Enter when done: '
read -r _unused

# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Write oci_config
# ─────────────────────────────────────────────────────────────────────────────

step "6/9" "Writing OCI config"

OCI_CONFIG="${SCRIPT_DIR}/oci_config"

cat > "$OCI_CONFIG" <<OCIEOF
[DEFAULT]
user=${USER_OCID}
fingerprint=${FINGERPRINT}
tenancy=${TENANCY_OCID}
region=${REGION}
key_file=${OCI_KEY}
OCIEOF

chmod 600 "$OCI_CONFIG"
ok "oci_config written"

# ─────────────────────────────────────────────────────────────────────────────
# Step 7 — Test API auth + discover OCIDs
# ─────────────────────────────────────────────────────────────────────────────

step "7/9" "Validating credentials and discovering your tenancy"

printf '  Contacting Oracle API...\n'

DISCOVERY_OUTPUT="$(python3 "${SCRIPT_DIR}/discover.py" "$OCI_CONFIG" "$TENANCY_OCID" 2>&1)" || {
    err "Oracle API call failed. Output:"
    printf '%s\n\n' "$DISCOVERY_OUTPUT"
    printf '  Common causes:\n'
    printf '  • API key not yet added in Oracle Console (wait ~30s and retry)\n'
    printf '  • Wrong tenancy or user OCID pasted\n'
    printf '  • Fingerprint mismatch (re-run ./setup.sh to regenerate)\n\n'
    exit 1
}

ok "Credentials valid"
printf '%s\n' "$DISCOVERY_OUTPUT"

# ─────────────────────────────────────────────────────────────────────────────
# Step 8 — Generate VM SSH key
# ─────────────────────────────────────────────────────────────────────────────

step "8/9" "Generating SSH key for your VM"

VM_KEY="${SCRIPT_DIR}/mariposa_vm_key"

if [ ! -f "$VM_KEY" ]; then
    ssh-keygen -t ed25519 -f "$VM_KEY" -N "" -C "mariposa-vm" -q
fi

VM_PUBKEY="$(cat "${VM_KEY}.pub")"
ok "SSH key ready: mariposa_vm_key  (keep this file — it's your only way in)"

# Inject SSH public key into config.json
python3 - "${SCRIPT_DIR}/config.json" "$VM_PUBKEY" <<'PYEOF'
import json, sys
path, pubkey = sys.argv[1], sys.argv[2]
with open(path) as f:
    cfg = json.load(f)
cfg["ssh_public_key"] = pubkey
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
PYEOF

# ─────────────────────────────────────────────────────────────────────────────
# Step 9 — Prompt for VM display name
# ─────────────────────────────────────────────────────────────────────────────

step "9/9" "VM display name"

prompt DISPLAY_NAME "Name for your VM in the Oracle Console" "mariposa-arm-01"

python3 - "${SCRIPT_DIR}/config.json" "$DISPLAY_NAME" <<'PYEOF'
import json, sys
path, name = sys.argv[1], sys.argv[2]
with open(path) as f:
    cfg = json.load(f)
cfg["display_name"] = name
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
PYEOF

ok "VM will be named: $DISPLAY_NAME"

# ─────────────────────────────────────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────────────────────────────────────

hr
printf '  \033[1;32mSetup complete!\033[0m\n\n'
printf '  Run the sniper:\n\n'
printf '      ./snipe.sh\n\n'
printf '  When capacity is found, your VM IP will print here and\n'
printf '  be saved to SUCCESS.txt. Then connect with:\n\n'
printf '      ssh -i mariposa_vm_key ubuntu@<ip>\n\n'
hr
