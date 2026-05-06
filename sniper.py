#!/usr/bin/env python3
"""
sniper.py — Oracle Cloud A1.Flex capacity sniper.

Polls every availability domain in your region until one has capacity,
then launches the VM and exits. Run via snipe.sh, not directly.
"""

import json
import logging
import random
import sys
import time
from pathlib import Path

import requests

try:
    import oci
except ImportError:
    print("ERROR: OCI SDK not installed. Run ./setup.sh first.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR   = Path(__file__).parent
CONFIG_FILE  = SCRIPT_DIR / "config.json"
OCI_CONFIG   = SCRIPT_DIR / "oci_config"
SUCCESS_FILE = SCRIPT_DIR / "SUCCESS.txt"

SHAPE          = "VM.Standard.A1.Flex"
OCPUS          = 4
MEMORY_GB      = 24
BOOT_VOLUME_GB = 50

POLL_BASE        = 60   # seconds between attempts
POLL_JITTER      = 30   # random extra seconds added each iteration
RATE_LIMIT_WAIT  = 300  # 5 min on first 429
RATE_LIMIT_MAX   = 1800 # 30 min max backoff

# ---------------------------------------------------------------------------
# Logging — stdout only, one line per attempt
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("sniper")


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print("ERROR: config.json not found. Run ./setup.sh first.")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_oci_config() -> dict:
    if not OCI_CONFIG.exists():
        print("ERROR: oci_config not found. Run ./setup.sh first.")
        sys.exit(1)
    cfg = oci.config.from_file(str(OCI_CONFIG), "DEFAULT")
    # Resolve key_file relative to script dir if it isn't absolute
    kf = Path(cfg["key_file"])
    if not kf.is_absolute():
        cfg["key_file"] = str(SCRIPT_DIR / kf)
    return cfg


def try_launch(oci_cfg: dict, cfg: dict, ad_name: str):
    """
    Attempt to launch in the given AD.

    Returns:
        ("success",   instance)   — launched
        ("capacity",  None)       — out of capacity, try next AD
        ("ratelimit", None)       — HTTP 429, back off
        ("auth",      msg)        — auth failure, stop
        ("quota",     msg)        — quota/limit exceeded, stop
        ("fatal",     msg)        — other non-transient error, stop
    """
    compute = oci.core.ComputeClient(oci_cfg)
    details = oci.core.models.LaunchInstanceDetails(
        compartment_id=cfg["compartment_id"],
        availability_domain=ad_name,
        shape=SHAPE,
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=OCPUS,
            memory_in_gbs=MEMORY_GB,
        ),
        display_name=cfg.get("display_name", "a1flex-vm"),
        image_id=cfg["image_id"],
        create_vnic_details=oci.core.models.CreateVnicDetails(
            subnet_id=cfg["subnet_id"],
            assign_public_ip=True,
        ),
        metadata={"ssh_authorized_keys": cfg["ssh_public_key"]},
        source_details=oci.core.models.InstanceSourceViaImageDetails(
            image_id=cfg["image_id"],
            boot_volume_size_in_gbs=BOOT_VOLUME_GB,
            source_type="image",
        ),
    )

    try:
        resp = compute.launch_instance(details)
        return ("success", resp.data)

    except oci.exceptions.ServiceError as e:
        status = e.status
        code   = (e.code or "").strip()
        msg    = (e.message or "").strip()

        if status == 429:
            return ("ratelimit", None)

        if status == 500 and (
            "Out of host capacity" in msg
            or "Out of capacity" in msg
            or code == "InternalError"
        ):
            return ("capacity", None)

        if status in (401, 403) or code in (
            "NotAuthenticated", "NotAuthorized", "InvalidSignedRequest"
        ):
            return ("auth", f"HTTP {status} [{code}]: {msg}")

        if "LimitExceeded" in code or "QuotaExceeded" in code \
                or "LimitExceeded" in msg or "QuotaExceeded" in msg:
            return ("quota", f"[{code}]: {msg}")

        return ("fatal", f"HTTP {status} [{code}]: {msg}")

    except (requests.ConnectionError, requests.Timeout, OSError) as e:
        return ("fatal", f"Network error: {e}")

    except Exception as e:
        return ("fatal", f"Unexpected error: {e}")


def get_public_ip(oci_cfg: dict, instance) -> str:
    """Poll until the primary VNIC has a public IP (up to 2 minutes)."""
    compute = oci.core.ComputeClient(oci_cfg)
    network = oci.core.VirtualNetworkClient(oci_cfg)
    deadline = time.time() + 120
    while time.time() < deadline:
        vnics = compute.list_vnic_attachments(
            compartment_id=instance.compartment_id,
            instance_id=instance.id,
        ).data
        for att in vnics:
            if att.lifecycle_state == "ATTACHED":
                vnic = network.get_vnic(att.vnic_id).data
                if vnic.public_ip:
                    return vnic.public_ip
        time.sleep(8)
    return "(IP not yet assigned — check Oracle Console)"


def main():
    cfg     = load_config()
    oci_cfg = load_oci_config()

    ad_names = cfg["ad_names"]
    region   = oci_cfg.get("region", "unknown")

    print()
    print(f"  Oracle A1.Flex sniper — region: {region}")
    print(f"  Shape: {SHAPE} | {OCPUS} OCPUs | {MEMORY_GB} GB RAM | {BOOT_VOLUME_GB} GB boot")
    print(f"  Polling {len(ad_names)} availability domain(s): {', '.join(ad_names)}")
    print(f"  Cadence: ~{POLL_BASE}-{POLL_BASE + POLL_JITTER}s between attempts")
    print(f"  Press Ctrl+C to stop.")
    print()

    ad_index      = 0
    attempt       = 0
    rate_backoff  = RATE_LIMIT_WAIT

    while True:
        ad = ad_names[ad_index % len(ad_names)]
        attempt += 1

        log.info("[attempt %d]  AD: %s  →  checking...", attempt, ad)
        result, data = try_launch(oci_cfg, cfg, ad)

        if result == "success":
            instance = data
            print()
            print("  ✓ Capacity found! Launching VM...")
            ip = get_public_ip(oci_cfg, instance)
            print()
            print("  ══════════════════════════════════════════════")
            print("  ✓  VM CREATED SUCCESSFULLY")
            print(f"     IP address : {ip}")
            print(f"     OCID       : {instance.id}")
            print(f"     AD         : {ad}")
            print()
            print(f"  Connect: ssh -i mariposa_vm_key ubuntu@{ip}")
            print("  ══════════════════════════════════════════════")
            print()

            SUCCESS_FILE.write_text(
                f"ip={ip}\nocid={instance.id}\nad={ad}\n"
            )
            sys.exit(0)

        elif result == "capacity":
            ad_index += 1
            sleep = POLL_BASE + random.uniform(0, POLL_JITTER)
            log.info("           ↳  out of capacity — next attempt in %.0fs", sleep)
            time.sleep(sleep)
            rate_backoff = RATE_LIMIT_WAIT  # reset on non-429

        elif result == "ratelimit":
            log.warning("           ↳  rate limited (429) — waiting %.0fs", rate_backoff)
            time.sleep(rate_backoff)
            rate_backoff = min(rate_backoff * 2, RATE_LIMIT_MAX)

        elif result == "auth":
            print()
            print(f"  ✗  Auth failure — stopping (looping would waste API quota).")
            print(f"     {data}")
            print()
            print("  Fix: check that your API key is still active in Oracle Console,")
            print("       then re-run ./setup.sh to refresh oci_config.")
            sys.exit(1)

        elif result == "quota":
            print()
            print("  ✗  Quota/limit exceeded — stopping.")
            print(f"     {data}")
            print()
            print("  This is not transient. Check your Oracle tenancy limits.")
            sys.exit(1)

        else:  # fatal
            print()
            print(f"  ✗  Fatal error — stopping.")
            print(f"     {data}")
            sys.exit(1)


if __name__ == "__main__":
    main()
