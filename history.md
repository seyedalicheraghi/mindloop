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

## 2026-06-21 — Domain + Cloudflare Tunnel: site is publicly live

- Ali registered **`mindsloop.org`** — on **GoDaddy**, not Cloudflare
  Registrar (his earlier "I registered in Cloudflare" referred to creating
  a Cloudflare account, not the domain purchase itself — clarified mid-session).
- Added the domain to Cloudflare via **"Connect a domain"** (not "Transfer"
  — GoDaddy domains are transfer-locked for ~60 days post-purchase anyway,
  and a transfer was never necessary; Cloudflare just needs to be
  authoritative DNS). Skipped importing DNS records (scan found 0 — fresh
  domain, no email/site previously configured). Confirmed DNSSEC was
  already off in GoDaddy.
- Updated GoDaddy nameservers from `ns27/ns28.domaincontrol.com` to
  Cloudflare's assigned `jeff.ns.cloudflare.com` / `leanna.ns.cloudflare.com`.
  Propagation took roughly 30-45 minutes; verified fully authoritative via
  `dig +trace` hitting the `.org` TLD servers directly.
- Ran `cloudflared tunnel login` (had to redo it once — the first attempt,
  before the domain was connected to Cloudflare, had no zone to authorize
  against and just hung on "Waiting for login..." indefinitely; killed and
  re-ran after the domain went active). Auth completed, `cert.pem` saved.
- Created tunnel `mindloop-portfolio` (id `00f3fb15-b170-4910-95ed-b5088b2a162f`).
  Config (`~/.cloudflared/config.yml`, later copied to `/etc/cloudflared/`)
  routes both `mindsloop.org` and `www.mindsloop.org` to
  `http://localhost:8080`, default `http_status:404` for anything else.
  Routed DNS for both hostnames (`cloudflared tunnel route dns`).
  Test-ran the tunnel in the foreground first — connectivity pre-checks
  all passed (quic, both regions, Cloudflare API) — and confirmed
  `https://mindsloop.org` and `https://www.mindsloop.org` both returned
  `200 OK` before making it permanent.
- Installed as a systemd service (`sudo cloudflared service install`) —
  needed the tunnel credentials JSON + `config.yml` copied into
  `/etc/cloudflared/` first, since running under `sudo` looks in *root's*
  home directory for the default config, not the invoking user's.
  `cloudflared` itself wasn't in the scoped sudoers allowlist (same
  one-off-password pattern as the earlier `usermod` snag), so this one
  command was run manually by Ali rather than extending the sudoers file
  for a single use.
- Final verification: both hostnames serve `200 OK` over HTTPS through
  Cloudflare; `docker`, `cloudflared`, `mindloop-rebuild.timer`, `ufw`, and
  `unattended-upgrades` are all `systemctl enabled` (persist across
  reboots). Took a third snapshot, `public-live`.

**State at end of this entry:** the portfolio site is fully live at
**https://mindsloop.org** and **https://www.mindsloop.org**, self-hosted on
the home PC, auto-redeploying on `git push` (within ~5 min via the rebuild
timer), firewalled, auto-patching, and with three VM rollback snapshots
(`pristine-install`, `working-baseline`, `public-live`). Everything in
`PLAN.md`'s original action list is now done. Remaining future work is
content — replacing the `PLACEHOLDER` markers in `content/projects/*.md`,
`data/experience.yaml`, `data/writing.yaml`, `content/about/_index.md`,
`content/contact/_index.md`, and adding a real `static/resume.pdf` — not
infrastructure.
