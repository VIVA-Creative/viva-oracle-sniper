#!/usr/bin/env python3
"""
discover.py — called by setup.sh to validate OCI credentials and write config.json.

Usage: python3 discover.py <oci_config_path> <tenancy_ocid>
"""

import json
import sys
from pathlib import Path

try:
    import oci
except ImportError:
    print("ERROR: OCI SDK not installed.", file=sys.stderr)
    sys.exit(1)

SHAPE      = "VM.Standard.A1.Flex"
OS_NAME    = "Canonical Ubuntu"
OS_VERSION = "24.04"


def main():
    if len(sys.argv) < 3:
        print("Usage: discover.py <oci_config> <tenancy_ocid>", file=sys.stderr)
        sys.exit(1)

    oci_config_path = sys.argv[1]
    tenancy_id      = sys.argv[2]
    script_dir      = Path(oci_config_path).parent

    cfg = oci.config.from_file(oci_config_path, "DEFAULT")
    # Resolve key_file relative to script dir
    kf = Path(cfg["key_file"])
    if not kf.is_absolute():
        cfg["key_file"] = str(script_dir / kf)

    identity = oci.identity.IdentityClient(cfg)
    compute  = oci.core.ComputeClient(cfg)
    network  = oci.core.VirtualNetworkClient(cfg)

    # --- Availability Domains ---
    ads = identity.list_availability_domains(tenancy_id).data
    ad_names = [ad.name for ad in ads]
    print(f"  Found {len(ad_names)} availability domain(s): {', '.join(ad_names)}")

    # --- Ubuntu 24.04 ARM image (most recent) ---
    images = oci.pagination.list_call_get_all_results(
        compute.list_images,
        tenancy_id,
        operating_system=OS_NAME,
        operating_system_version=OS_VERSION,
        shape=SHAPE,
        sort_by="TIMECREATED",
        sort_order="DESC",
    ).data

    arm_images = [
        i for i in images
        if "aarch64" in (i.display_name or "").lower()
        or "arm"     in (i.display_name or "").lower()
        or i.launch_mode == "NATIVE"
    ]
    image = arm_images[0] if arm_images else (images[0] if images else None)
    if not image:
        print(f"ERROR: No Ubuntu {OS_VERSION} ARM image found for shape {SHAPE}.",
              file=sys.stderr)
        print("  Your region may not support A1.Flex — try us-ashburn-1 or us-phoenix-1.",
              file=sys.stderr)
        sys.exit(1)
    print(f"  Image: {image.display_name}")

    # --- Public subnet (from first VCN with one) ---
    vcns = oci.pagination.list_call_get_all_results(
        network.list_vcns, tenancy_id).data
    if not vcns:
        print("ERROR: No VCNs found in your tenancy.", file=sys.stderr)
        print("  Oracle creates a default VCN automatically — if you don't see one,",
              file=sys.stderr)
        print("  go to Networking → Virtual Cloud Networks → Start VCN Wizard.",
              file=sys.stderr)
        sys.exit(1)

    subnet_id   = None
    subnet_name = None
    for vcn in vcns:
        subnets = oci.pagination.list_call_get_all_results(
            network.list_subnets, tenancy_id, vcn_id=vcn.id).data
        public = [
            s for s in subnets
            if not s.prohibit_public_ip_on_vnic
            and s.lifecycle_state == "AVAILABLE"
        ]
        if public:
            subnet_id   = public[0].id
            subnet_name = public[0].display_name
            break

    if not subnet_id:
        print("ERROR: No public subnet found.", file=sys.stderr)
        print("  Make sure your VCN has a public subnet with public IPs enabled.",
              file=sys.stderr)
        sys.exit(1)
    print(f"  Subnet: {subnet_name}")

    # --- Write config.json ---
    config_file = script_dir / "config.json"
    config = {
        "compartment_id": tenancy_id,
        "ad_names":       ad_names,
        "image_id":       image.id,
        "subnet_id":      subnet_id,
        "display_name":   "mariposa-arm-01",
        "ssh_public_key": "",
    }
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print("  config.json written.")


if __name__ == "__main__":
    main()
