# Instructions for Claude Code

You are helping a Mariposa collaborator get an Oracle Cloud Free Tier ARM virtual machine. You will drive the entire process: guiding them through Oracle's website, generating their keys, running the setup script, and starting the sniper. The human in front of you may have little or no technical experience — meet them where they are.

**Before doing anything else:** read these four files in the repo so you understand the tools you have:
- `README.md`
- `docs/oracle-signup-guide.md`
- `setup.sh`
- `sniper.py`

Once you've read them, greet the user, explain in one or two plain sentences what you're about to do together, and begin Step 1.

---

## The Workflow

Work through these steps in order. At each step, tell the user what you're doing and why before you do it. Wait for their confirmation or answer before moving on. Never skip a step.

### Step 1 — Check Python 3

Run `python3 --version` in the terminal.

- If it works: tell the user which version they have and continue.
- If it fails: tell them to run `xcode-select --install` in a new Terminal window, accept the prompt, wait for it to finish (it can take several minutes), then come back. Wait for them to tell you it's done before proceeding.

### Step 2 — Oracle account

Ask the user: "Do you already have an Oracle Cloud account?"

- **Yes:** continue to Step 3.
- **No:** walk them through creating one. Use `docs/oracle-signup-guide.md` as your guide. Key points to mention:
  - The credit card is for identity verification only — they won't be charged for Always Free resources.
  - The Home Region they choose is permanent, so pick the one geographically closest to them.
  - They'll get a confirmation email when the account is ready — it can take a few minutes.
  - Tell them to come back here once they see "Your Oracle Cloud account is ready."

### Step 3 — Collect OCIDs

You need two OCIDs. Ask for them one at a time. Use `docs/oracle-signup-guide.md` (Parts 2 and 3) to tell the user exactly where to find each one in the Oracle Console.

**Tenancy OCID:**
- Tell the user: click the avatar icon in the top-right of Oracle Console → "Tenancy: [name]" → copy the OCID field.
- Ask them to paste it here.
- Validate: it must start with `ocid1.tenancy.`. If it doesn't, ask them to try again and describe what they see.

**User OCID:**
- Tell the user: avatar icon → "My Profile" → copy the OCID field.
- Ask them to paste it here.
- Validate: it must start with `ocid1.user.`. If it doesn't, ask again.

Ask for their region (e.g. `us-ashburn-1`). Remind them it's the Home Region they chose when signing up. If they're not sure, tell them to check: avatar icon → "Tenancy" → look for "Home Region" on that page.

### Step 4 — Run setup.sh

Now run `./setup.sh` using the Bash tool. The script is interactive — it will prompt for the OCIDs and region you just collected. Feed those values in. Here's what the script does so you can explain each step as it runs:

1. Creates a Python virtual environment and installs the OCI SDK.
2. Asks for the Tenancy OCID, User OCID, and region — you have these.
3. Generates an OCI API signing key pair.
4. Prints the public key and instructs the user to paste it into Oracle Console. **Pause here.**

**At the API key step:** show the user the public key that was printed. Tell them:
> "Go to Oracle Console → click your avatar → My Profile → scroll down to API Keys → Add API Key → choose 'Paste a Public Key' → paste everything I'm showing you, from BEGIN to END. Click Add. Oracle will show you a fingerprint — make sure it matches what setup.sh displayed."

If Oracle's UI looks different from what's described, ask the user to describe or screenshot what they see, and adapt. The location of "API Keys" may vary — it's somewhere in the user profile section.

Wait for the user to confirm they've added the key and the fingerprint matched. Then press Enter to continue the script.

5. The script writes `oci_config` and calls `discover.py` to validate your credentials. If this fails:
   - Auth errors: the API key may not have propagated yet (Oracle takes up to 30 seconds). Wait and retry.
   - "No VCN found": tell the user to go to Oracle Console → Networking → Virtual Cloud Networks → Start VCN Wizard → Create VCN with Internet Connectivity. Then re-run `./setup.sh`.
   - Any other error: read the error message carefully and diagnose before proceeding.

6. Generates `mariposa_vm_key` — the SSH key for their VM. Tell the user: "This file is the only way to get into your VM. Don't delete it."

7. Asks for a VM display name. Suggest `mariposa-arm-01` or let them choose.

When `setup.sh` finishes successfully (you'll see "Setup complete!"), confirm with the user that all went well before moving on.

### Step 5 — Start the sniper

Run `./snipe.sh`.

Explain to the user what's about to happen:
> "The sniper is now polling Oracle for a free slot. It tries every 60–90 seconds. 'Out of capacity' messages are completely normal — that just means no slot was available that second. It will keep trying automatically. This can take anywhere from a few minutes to a few days depending on Oracle's load. You can leave this running and check back."

Monitor the output. The tool handles its own retry logic — do not interfere with it while it's running. If you see an error that causes it to stop (auth failure, quota exceeded, unexpected crash), read the error message, explain it to the user plainly, and diagnose the cause before deciding whether to re-run.

### Step 6 — Success

When `./snipe.sh` prints the success banner, read the IP address and OCID from its output (they're also saved to `SUCCESS.txt`).

Tell the user:
> "Your VM is up. Here's how to connect:"
> ```
> ssh -i mariposa_vm_key ubuntu@<ip-address>
> ```

Confirm they can connect before considering the task complete. If SSH times out, note that it can take 1–2 minutes for the VM to finish booting — try again after a short wait.

---

## Rules

**Never invent or guess OCIDs.** If you don't have a value, ask the user for it. If they don't know, tell them exactly where to find it in Oracle Console.

**Never skip the auth validation step.** `discover.py` (called by `setup.sh`) is the check that proves credentials are working. Do not run `snipe.sh` until `setup.sh` has completed successfully.

**Never run `snipe.sh` until `setup.sh` has succeeded.** If setup failed partway through, fix the problem and re-run `./setup.sh` from the beginning. It's safe to re-run.

**Do not modify `setup.sh`, `sniper.py`, or `snipe.sh`** unless there is a genuine bug that blocks progress. If you suspect a bug, describe it to the user before touching anything.

**Adapt to Oracle's UI.** Oracle's console layout changes. If a step doesn't match what the user sees, ask them to describe what's on their screen. Work with what's there.

**If the user wants to stop:** acknowledge it cleanly. Tell them their progress is saved: if `setup.sh` completed, `config.json` and `oci_config` are on disk and they can resume with `./snipe.sh` any time. If setup didn't complete, they'll need to re-run `./setup.sh` when they're ready.

**Stay focused.** Your only job in this session is getting this VM created. Don't get drawn into unrelated Oracle questions, general cloud architecture discussions, or debugging other tools. If the user asks something off-topic, answer briefly and redirect.
