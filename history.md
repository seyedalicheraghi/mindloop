# Project History

Chronological log of significant actions taken on this project — by Ali or
any agent. Append-only, full history (not capped). See `CLAUDE.md` for the
logging rule, and `PLAN.md` for the architecture this history is executing
against.

## 2026-06-20 — Scaffold the Hugo-based portfolio site

Scaffolded the Hugo content/layout structure (Hero, About, Projects, Skills,
Experience, Writing, Contact), placeholder content for 3 illustrative
ML/CV/LLM projects, a hand-written CSS theme (no JS, auto dark mode),
`Dockerfile` (multi-stage Hugo build -> Caddy serve) + `Caddyfile`, and
Python rebuild automation under `deploy/rebuild/`. Scaffold-only pass — no
VM, no installs, no domain, no Cloudflare Tunnel, no git push. See
`README.md` for full details.

## 2026-06-20/21 — Set up the home-PC VM (`mindloop-vm`)

- Diagnosed `virt-manager` "Unable to connect to libvirt qemu:///system"
  error: user `ali` was already in the `libvirt`/`kvm` groups per
  `/etc/group`, but the active desktop session had a stale group list
  (added after login). Workaround: `sg libvirt -c virt-manager` / `sg
  libvirt -c <cmd>` to run with the group active without a full logout.
  Permanent fix requires a logout/reboot.
- Created `mindloop-vm` in virt-manager (1 vCPU / 1-2GB RAM, no GPU
  passthrough — deliberately small since the host is also used for ML
  training/inference) with an Ubuntu Server 26.04 ISO
  (`/home/ali/Downloads/ubuntu-26.04-live-server-amd64.iso`).
- Hit a SeaBIOS "No bootable device" error on first boot. Diagnosis: the
  New VM wizard never actually attached a CD-ROM device (only the blank
  `vda` virtio disk existed; boot order was `hd`-only). Fixed by:
  - Force-stopping the VM (`virsh destroy`, safe since nothing had booted).
  - Attaching the ISO as a SATA CD-ROM device:
    `virt-xml mindloop-vm --add-device --disk <iso-path>,device=cdrom,bus=sata`
  - Setting boot order to `cdrom,hd`: `virt-xml mindloop-vm --edit --boot cdrom,hd`
  - Hit a second blocker: qemu (running as user `libvirt-qemu`) couldn't
    traverse `/home/ali` (mode `750`) to reach the ISO in `~/Downloads`.
    Fixed with a minimal POSIX ACL (no sudo needed, no broad permission
    change): `setfacl -m u:libvirt-qemu:--x /home/ali`.
  - Verified via `virsh screenshot` that it booted into the Ubuntu Server
    GRUB menu / Subiquity installer.
- Walked through the Subiquity installer:
  - Network: auto-DHCP on the default NAT network (`enp1s0`, got
    `192.168.122.104/24`) — correct, since the VM only needs outbound
    connectivity (GitHub polling, outbound-only Cloudflare Tunnel later),
    no static IP or bridged networking needed.
  - Proxy: left blank (home network, no corporate proxy).
  - SSH: installed OpenSSH server; imported the SSH key from GitHub
    (`seyedalicheraghi`) rather than enabling password auth — the local
    `~/.ssh/id_ed25519.pub` was confirmed already registered there
    (`curl https://github.com/seyedalicheraghi.keys`).
  - Featured server snaps: selected none — none were relevant (Docker
    wasn't even in the list; only this VM needs plain Docker via apt later,
    not snap, to avoid snap confinement quirks).
  - Username set during Profile setup: **`mindloop2026ali`**.
- After install completed and the VM rebooted, it looped back to the
  installer's language screen — expected, since boot order still had
  `cdrom` first and the ISO remains bootable indefinitely. Confirmed the
  install had actually succeeded (disk allocation grew from ~4MB to ~6GB
  via `virsh domblkinfo mindloop-vm vda`), then fixed permanently:
  - Force-stopped the VM.
  - Removed the CD-ROM device: `virt-xml mindloop-vm --remove-device --disk device=cdrom`
  - Reset boot order to `hd` only: `virt-xml mindloop-vm --edit --boot hd`
  - Verified via screenshot it now boots straight into the installed OS
    (`mindloop-vm login:` prompt, Ubuntu 26.04 LTS).
- Verified SSH access end-to-end: `ssh mindloop2026ali@192.168.122.104`
  works with the imported key, user is in the `sudo` group.
- Added a DHCP reservation on the libvirt `default` network so
  `mindloop-vm` always gets `192.168.122.104` (MAC `52:54:00:67:54:e3`),
  persisted across host/libvirtd restarts:
  ```
  virsh net-update default add ip-dhcp-host \
    "<host mac='52:54:00:67:54:e3' name='mindloop-vm' ip='192.168.122.104'/>" \
    --live --config
  ```

**State at end of this entry:** `mindloop-vm` is installed, boots cleanly,
reachable via SSH at a stable reserved IP. Next per `PLAN.md`: install
Docker inside the VM (official apt repo, not snap), then proceed to
domain registration / Cloudflare Tunnel setup.

## 2026-06-21 — Docker, GitHub push, rebuild automation, VM hardening

- Snapshotted `mindloop-vm` (`pristine-install`) before installing anything
  — this was skipped in the prior entry, caught and fixed here.
- Fixed `deploy/mindloop-rebuild.service`'s hardcoded `User=mindloop` ->
  `User=mindloop2026ali` (actual VM username).
- Excluded `.claude/` (agent tooling/internal memory) from version control
  via `.gitignore` before the first commit — not portfolio content, no
  reason to publish internal agent notes to a public repo.
- `git init`, initial commit, and `gh repo create seyedalicheraghi/mindloop
  --public --source=. --remote=origin --push` — project is now live at
  https://github.com/seyedalicheraghi/mindloop
- Added a scoped `/etc/sudoers.d/mindloop-setup` NOPASSWD drop-in for
  `mindloop2026ali` (specific binaries only: `apt-get`, `apt`, `mkdir`,
  `chown`, `cp`, `install`, `tee`, `curl`, `chmod`, `systemctl`, `ufw`,
  `dpkg-reconfigure` — plus `/usr/bin/usermod`, which turned out to be the
  wrong path on this system; the real binary is `/usr/sbin/usermod`, so
  that one command was run manually with a password instead of fixing the
  sudoers entry, since it was a single one-off use).
- Installed Docker via the official apt repo (`download.docker.com` —
  confirmed the brand-new `resolute` (26.04) suite is already published
  there, no `noble` fallback needed). Added `mindloop2026ali` to the
  `docker` group.
- Created `/opt/mindloop` (sudo chown to `mindloop2026ali`), cloned the
  repo there via HTTPS (no SSH key needed on the VM — repo is public,
  read-only access is all the rebuild automation ever needs).
- Built the image (`docker build -t mindloop-portfolio:latest .` — Hugo
  build: 22 pages, clean) and ran it (`--read-only`, tmpfs `/data`+`/config`,
  `-p 8080:8080`, `--restart unless-stopped`). Verified `curl -sI
  localhost:8080` returns `200 OK` from Caddy with security headers.
- Installed `mindloop-rebuild.service`/`.timer` into
  `/etc/systemd/system/`, enabled the timer. First run logged "No remote
  changes; skipping rebuild" — correct, since the container was already
  current.
- Hardened the VM: `ufw` enabled with default-deny incoming, outgoing
  allowed, SSH allowed only from `192.168.122.1` (the host) — confirmed via
  `ss -tln` that only `:8080` and `:22` are listening. Enabled
  `unattended-upgrades`.
- Took a second snapshot, `working-baseline`, capturing this fully-working
  state (site serving internally, auto-redeploy active, firewall +
  auto-updates on) — before any Cloudflare Tunnel work.

**State at end of this entry:** site is fully functional and
auto-redeploying *inside* the VM/home network, but not yet reachable from
the public internet. **Deliberately deferred** (needs Ali's direct action —
payment info, browser login — can't be automated): domain registration,
`cloudflared` install + `cloudflared tunnel login`, creating the tunnel,
attaching the domain, and verifying public HTTPS.
