# Oracle Cloud Free Tier — Signup & Setup Guide

This walks you through creating an Oracle Cloud account and finding the two pieces of information that `setup.sh` asks for.

---

## Part 1 — Create a Free Tier account

1. Go to **https://www.oracle.com/cloud/free/**
2. Click **Start for free**
3. Enter your name, work email, and home country
4. Verify your email address when Oracle sends you a confirmation
5. Choose a **Cloud Account Name** — this is just a label for your tenancy, anything works
6. Choose the **Home Region** closest to you:
   - US East: `us-ashburn-1` (Virginia)
   - US West: `us-phoenix-1` (Arizona)
   - Europe: `eu-frankfurt-1`, `uk-london-1`
   - Asia Pacific: `ap-tokyo-1`, `ap-sydney-1`

   > ⚠️ You cannot change your Home Region after signup. The A1.Flex (ARM) instance must be in your Home Region.

7. Enter a credit card for identity verification — **you will not be charged** as long as you only use Always Free resources
8. Complete phone verification
9. Wait for the confirmation email: **"Your Oracle Cloud account is ready"**

---

## Part 2 — Find your Tenancy OCID

The Tenancy OCID identifies your entire Oracle Cloud account.

1. Log in at **https://cloud.oracle.com**
2. Click the **avatar / profile icon** in the top-right corner
3. Click **Tenancy: [your account name]**
4. On the Tenancy detail page, find the **OCID** field near the top
5. Click **Copy** next to it

It looks like:  
`ocid1.tenancy.oc1..aaaaaaaa[long string of letters and numbers]`

---

## Part 3 — Find your User OCID

The User OCID identifies your login (the account you're signed in as).

1. Click the **avatar / profile icon** in the top-right corner
2. Click **My Profile**
3. On the profile page, find the **OCID** field near the top
4. Click **Copy** next to it

It looks like:  
`ocid1.user.oc1..aaaaaaaa[long string of letters and numbers]`

---

## Part 4 — Add the API signing key (setup.sh handles this)

`setup.sh` generates a key pair for you and prints the public key. Here's where to paste it:

1. Click the **avatar / profile icon** → **My Profile**
2. Scroll down to **API Keys** (under Resources on the left)
3. Click **Add API Key**
4. Select **Paste a Public Key**
5. Paste the public key that `setup.sh` printed (the entire block from `-----BEGIN PUBLIC KEY-----` to `-----END PUBLIC KEY-----`)
6. Click **Add**
7. Oracle shows a **Configuration File Preview** — note the **Fingerprint** value (e.g. `ab:cd:ef:...`)
8. Verify it matches what `setup.sh` showed you, then press Enter in Terminal to continue

---

## Part 5 — Understand your Always Free quota

Oracle Always Free gives you:

- **4 OCPUs + 24 GB RAM** of A1.Flex (ARM) — shared across up to 4 instances
- **200 GB** total block volume storage
- **2** AMD E2 Micro instances (1 OCPU, 1 GB RAM each) — you may already have one

The sniper will create **one A1.Flex VM using the full free quota** (4 OCPUs, 24 GB RAM, 50 GB boot volume). If you already have an A1.Flex instance, it will fail with a quota error.

---

## Troubleshooting

**"The requested VM shape is not available in this region"**  
A1.Flex is only available in Home Regions. If you signed up in a region that doesn't yet support it, you may need to create a new account with a different home region.

**"Out of capacity" — always**  
This is normal — everyone wants free ARM VMs. The sniper handles this automatically and keeps retrying. A slot usually opens within a few hours to a few days.

**Auth errors after running setup.sh**  
Wait 30 seconds after adding the API key in Oracle Console, then re-run `./setup.sh`. Key activation can take a moment.

**"No VCN found"**  
Oracle creates a default VCN automatically when you first log in. If you dismissed the setup wizard, go to:  
Networking → Virtual Cloud Networks → **Start VCN Wizard** → Create VCN with Internet Connectivity.
