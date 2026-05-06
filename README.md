# Oracle A1.Flex Sniper

Polls Oracle Cloud for an ARM VM slot and creates it the moment one opens up. Runs on your Mac, talks only to Oracle's API, exits when done.

**Why:** Oracle's free-tier A1.Flex instances (4 OCPUs, 24 GB RAM) are always sold out. Slots open randomly. This tool keeps trying so you don't have to.

---

## What you get

One `VM.Standard.A1.Flex` instance in your Oracle Free Tier tenancy:
- 4 OCPUs, 24 GB RAM
- 50 GB boot volume, Ubuntu 24.04 ARM
- Public IP address
- SSH access via the key the tool generates for you

---

## Prerequisites

- macOS 13 or later
- Python 3 — comes with Xcode Command Line Tools. If you don't have it:
  ```
  xcode-select --install
  ```
  Accept the prompt, wait for it to finish, then continue.
- An Oracle Cloud Free Tier account — see [docs/oracle-signup-guide.md](docs/oracle-signup-guide.md)

---

## Quickstart

```bash
# 1. Clone the repo
git clone https://github.com/VIVA-Creative/viva-oracle-sniper.git
cd viva-oracle-sniper

# 2. Run setup (one time only — ~5 minutes)
chmod +x setup.sh snipe.sh
./setup.sh

# 3. Start sniping
./snipe.sh
```

`setup.sh` walks you through everything interactively: it collects your Oracle credentials, generates keys, validates your auth, and discovers the right image and subnet for your region automatically.

`./snipe.sh` then polls Oracle every 60–90 seconds until a slot opens. When it does:

```
  ══════════════════════════════════════════════
  ✓  VM CREATED SUCCESSFULLY
     IP address : 138.x.x.x
     OCID       : ocid1.instance.oc1...
     AD         : abcd:US-ASHBURN-AD-2

  Connect: ssh -i mariposa_vm_key ubuntu@138.x.x.x
  ══════════════════════════════════════════════
```

The IP and OCID are also saved to `SUCCESS.txt`.

---

## Files created during setup (gitignored — yours only)

| File | Contents |
|------|----------|
| `oci_config` | Your Oracle API credentials |
| `oci_api_key.pem` | Private key for Oracle API auth |
| `oci_api_key_public.pem` | Public key (uploaded to Oracle Console) |
| `mariposa_vm_key` | Private SSH key for your new VM |
| `mariposa_vm_key.pub` | Public SSH key (installed on VM at creation) |
| `config.json` | Discovered OCIDs for your region (ADs, image, subnet) |
| `.venv/` | Python virtual environment |

> **Back up `mariposa_vm_key`** — it's the only way to SSH into your VM.

---

## Polling behavior

- Tries each availability domain in rotation
- 60–90 second pause between attempts (adds random jitter to avoid synchronized hammering)
- On HTTP 429 (rate limited): backs off starting at 5 minutes, doubles each time up to 30 minutes
- On auth or quota errors: stops immediately with a clear message (retrying would waste API calls)
- Press `Ctrl+C` to stop at any time

---

## Re-running setup

If your credentials expire or you need to re-authenticate, just run `./setup.sh` again. It regenerates the OCI API key and rewrites `oci_config`. You'll need to remove the old key from Oracle Console and add the new one.

---

## Oracle signup guide

New to Oracle Cloud? See [docs/oracle-signup-guide.md](docs/oracle-signup-guide.md) for a step-by-step walkthrough including where to find your OCIDs and how to add the API key.
