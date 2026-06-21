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

## 2026-06-21 — Found and fixed a reboot gap: the VM itself didn't autostart

While documenting the recovery process for the README, checked what
actually happens if the home PC reboots — found that the libvirt `default`
network was set to autostart (`yes`), and `libvirtd` itself starts on host
boot (`systemctl is-enabled libvirtd` -> `enabled`), but **`mindloop-vm`
itself was not** (`virsh dominfo mindloop-vm` showed `Autostart: disable`).
Without this, a host reboot would bring the network up but leave the VM
powered off indefinitely until someone manually ran `virsh start
mindloop-vm` — the site would silently stay down with no automatic
recovery at all.

- Fixed: `virsh autostart mindloop-vm` -> now `Autostart: enable`.
- Verified the *inside-the-VM* half of recovery by rebooting the VM itself
  (`virsh reboot mindloop-vm` — safe, only restarts the guest, not the host
  PC): confirmed `docker`, `cloudflared`, `mindloop-rebuild.timer`, `ufw`,
  and `unattended-upgrades` all came back `active` on their own, and the
  `mindloop-portfolio` container restarted automatically (`--restart
  unless-stopped` on `docker run` is what does this — no systemd unit
  manages the container itself, the restart policy is stored in Docker's
  own container config). Confirmed `https://mindsloop.org` was reachable
  again within seconds.
- **Not verified by an actual test** (deliberately — rebooting the whole
  host PC would interrupt Ali's other work, e.g. ML training): a *full
  host reboot*, where `mindloop-vm`'s new autostart flag is what brings the
  guest up in the first place. The fix is applied and the config is
  confirmed correct, but the very first real host reboot is the first time
  this exact path gets exercised end-to-end. Worth a quick sanity check
  next time the host reboots for any reason (`virsh list --all` should
  show `mindloop-vm` as `running` shortly after the host comes up, with no
  manual `virsh start` needed).

## Challenges & lessons learned (cumulative, across this whole project)

Patterns worth remembering for next time, not just what happened once:

- **Stale login-session group membership bit twice.** Adding a user to a
  group (`libvirt`, `docker`) doesn't take effect in any shell/session that
  was already open — `id`/`groups` in an old session won't show it even
  though `/etc/group` is already correct. `sg <group> -c "command"` is the
  reliable one-off workaround; a full logout/login (or new SSH session for
  remote work) is the permanent fix. Symptom to recognize: a permission
  error right after you were "definitely already added to that group."
- **qemu/Docker run as their own restricted users, not as you.** Two
  separate permission surprises came from this: `libvirt-qemu` couldn't
  traverse `/home/ali` (mode `750`) to read an ISO in `~/Downloads` even
  though the file itself was readable — fixed with a scoped POSIX ACL
  (`setfacl -m u:libvirt-qemu:--x /home/ali`) rather than loosening the
  whole directory. And `sudo <cmd>` run as root looks for config files in
  *root's* home directory, not the invoking user's — `cloudflared service
  install` failed until the tunnel config was copied to `/etc/cloudflared/`
  explicitly.
- **`sudo -n true` is not a valid "is passwordless sudo working" test.**
  It only tells you whether the specific command `true` is passwordless —
  if your NOPASSWD rule is scoped to specific binaries (as this project's
  is, deliberately, rather than blanket `ALL`), you have to test with one
  of *those* binaries (e.g. `sudo -n /usr/bin/apt-get --version`). Wasted a
  round-trip on this exact mistake mid-project.
- **Scoped sudoers rules need the *real* binary path, not the conventional
  one.** `/usr/bin/usermod` looked right but was wrong on this system — the
  real binary was `/usr/sbin/usermod`. Same class of issue would apply to
  any future scoped sudoers addition: always confirm with `which <cmd>`
  before adding it to the allowlist, don't assume `/usr/bin/`.
  `cloudflared` itself was never added to the allowlist at all (a one-off
  command didn't justify widening the policy), so that single command was
  always going to need a manually-typed password — expected, not a bug.
- **A brand-new Ubuntu release's codename can 404 on third-party apt
  repos.** Ubuntu 26.04 ("resolute") was new enough that this was a real
  risk for both Docker's and Cloudflare's repos. Docker's repo happened to
  already support `resolute` by the time this was done; Cloudflare's did
  not, and needed an explicit fallback to `noble`. Always have the
  fallback ready rather than assuming either way.
- **A Cloudflare "tunnel login" can hang forever for a reason that looks
  like nothing is happening.** The first `cloudflared tunnel login` attempt
  just sat at "Waiting for login..." indefinitely — not because anything
  was broken, but because the domain hadn't been added to Cloudflare yet,
  so there was no zone to authorize against. If this hangs, check the
  domain/zone state before assuming the login flow itself is broken.
- **"Add a site" in Cloudflare's current UI is split into three buttons**
  ("Connect a domain" / "Transfer a domain" / "Buy a domain") where older
  guides just say "Add a Site." For a domain already owned elsewhere and
  not being moved, the answer is always "Connect a domain" — "Transfer"
  is a different, slower, registrar-changing operation (and is usually
  blocked for ~60 days on a freshly-purchased domain anyway).
- **DNS propagation delay is real but easy to mistake for a config error.**
  GoDaddy's nameserver change took roughly 30-45 minutes to become
  authoritative. A `dig` from a local/cached resolver can lag well behind
  reality — checking directly against `1.1.1.1`/`8.8.8.8`, or with `dig
  +trace` against the TLD's own authoritative servers, is the way to tell
  "actually not propagated yet" apart from "propagated, but something
  local is just caching the old answer." The latter happened twice in this
  project (once for the nameserver switch, once for the `www` CNAME) and
  both times the fix was just querying a different resolver, not waiting
  longer.
- **A skipped "do this immediately after X" step doesn't announce itself.**
  The plan called for a VM snapshot immediately after fresh install, before
  installing anything else — it got skipped in the moment and only caught
  later because a checklist existed to catch it. Same pattern repeated
  with VM autostart in this entry: a one-line config step with no error
  message if it's missing, only discovered by deliberately asking "what
  actually happens if X" instead of assuming the happy path was covered.

## 2026-06-21 — Real social links, modernized design (CSS-only depth)

- Added real LinkedIn (`linkedin.com/in/sacheraghi`) and Google Scholar
  links to `content/contact/_index.md`, and fixed the GitHub link from a
  `PLACEHOLDER` to the real profile. Added a `scholar` field rendered by
  `layouts/contact/list.html`.
- Ali asked to "make it more modern with 3D images and everything." Before
  touching design, clarified scope via two quick questions rather than
  guessing: (1) whether "3D" meant literal 3D graphics (Three.js/WebGL —
  would require adding JavaScript and abandoning the site's deliberate
  zero-JS architecture) or CSS-only depth effects (hover tilts, layered
  shadows, glassmorphism — no JS needed); Ali chose the latter. (2) whether
  he had a reference site in mind, or wanted a proposed direction; he chose
  the latter.
- Rewrote `static/css/main.css`: gradient-clipped hero name text, two
  blurred floating "glow blob" pseudo-elements behind the hero (pure CSS
  `filter: blur()` + `@keyframes`, no images), glassmorphism cards
  (`backdrop-filter: blur()` + translucent background) with a CSS-only 3D
  tilt-and-lift on hover (`transform: perspective() rotateX() rotateY()
  translateY()`), a sticky frosted-glass nav bar, gradient pill-shaped
  buttons, and a `prefers-reduced-motion` override that disables all of the
  above for users who've asked for less motion. Zero JavaScript added —
  architecture unchanged.
- **Verified in an actual browser before calling it done** (per this
  project's "always run frontend changes" convention), using the `run`
  skill: started `hugo server -D` locally, drove headless Chrome
  (`google-chrome --headless=new`) to screenshot the homepage, a project
  page, the contact page, and the skills page, in both light and forced-
  light mode plus a mobile viewport width.
- **Caught a screenshot-tooling artifact, not a real bug:** the first
  screenshot showed the gradient hero text almost invisible against the
  dark background. Root cause wasn't the CSS — `hero-rise` is a 0.7s
  fade-in-on-page-load animation, and Chrome's `--screenshot` flag
  captures immediately after load, mid-animation. Re-shot with
  `--virtual-time-budget=3000` to let it settle, confirmed the gradient
  text, glow blobs, and cards all render correctly. Lesson: when
  screenshotting a page with load-triggered CSS animations, always give
  it time to settle before judging the result — don't mistake "still
  animating" for "broken."
- All pages confirmed clean in light mode, dark mode (the default in this
  headless Chrome environment), and a 390px mobile width — no overflow, no
  illegible text, nav collapses correctly on mobile.
- Pushed to `main`; the VM's rebuild timer will pick it up and redeploy
  within ~5 minutes (no manual VM-side action needed for a content/static
  asset change).

## 2026-06-21 — Found and fixed: Cloudflare was serving stale CSS

Ali reported the redesign wasn't visible on `mindsloop.org` shortly after
the previous entry's deploy. Diagnosis: `curl -sI
https://mindsloop.org/css/main.css` showed `cf-cache-status: HIT`,
`cache-control: max-age=14400` (4 hours), and a `last-modified` timestamp
from *before* the redesign — Cloudflare's edge had cached the old
`/css/main.css` and kept serving it, because the URL never changed between
deploys (no cache-busting), so the CDN had no signal that the content
underneath that exact path had changed. The site itself had redeployed
correctly (confirmed via the rebuild timer's logs) — this was purely a
caching problem, not a deployment failure.

**Permanent fix, not just a one-off purge:** moved `static/css/main.css`
to `assets/css/main.css` and switched `layouts/partials/head.html` to
Hugo's asset pipeline (`resources.Get "css/main.css" | fingerprint`),
which outputs a content-hashed filename (e.g.
`main.fdd0e939....css`) and a Subresource Integrity hash. Because the
filename itself changes whenever the CSS content changes, every future
deploy automatically gets a brand-new URL — Cloudflare and browsers can
cache it as aggressively and as long as they want, since a stale cache
entry for the *old* filename is harmless (nothing references that URL
anymore) and the *new* filename has never been cached, so it's always a
fresh fetch. This needed no Cloudflare dashboard changes or API access —
fixed entirely from the Hugo template/build side.
- Verified the fix locally first (`hugo --minify --gc`, confirmed the
  hashed filename in `public/index.html`, screenshotted via headless
  Chrome to confirm styles still applied identically) before pushing.
- Triggered the VM's rebuild manually (`sudo systemctl start
  mindloop-rebuild.service`) rather than waiting for the timer, then
  confirmed end-to-end: the new fingerprinted CSS URL returns
  `cf-cache-status: MISS` (fresh, not a stale hit) and contains the new
  design rules. Screenshotted the real public `https://mindsloop.org/`
  directly to visually confirm.

**Lesson for future static-asset changes:** any time a *static asset's
content* changes but its *URL* doesn't, a CDN sitting in front of it (or
even just a visitor's browser cache) can mask the change indefinitely,
even though the deploy itself succeeded. Fingerprinted/hashed filenames
are the standard fix — they make "did the deploy actually take effect"
trivially checkable (new hash in the HTML = new content shipped) instead
of needing to manually inspect cache headers.

## 2026-06-21 — Bolder colors + real publications (Ali: "boring, no color, not enough info")

Ali said the site looked boring with no color and not enough information.
Split into two distinct problems via clarifying questions rather than
guessing which one to fix:

1. **Color**: wanted a bolder, more vibrant palette (confirmed, not "add
   real photos" — that's separate, still open).
2. **Information**: confirmed it meant replacing `PLACEHOLDER` text with
   real content, not "add more sections."

**Color fix**: added two more accent hues (pink `--color-accent-3`, amber
`--color-accent-4`) on top of the existing blue/purple, so the hero
gradient text and glow blobs now span 4 colors instead of 2. Added a
gradient top accent bar on every card that rotates through the palette by
position (`nth-child`), gradient-underlined `h2` headings, and color-coded
pills (rotating text/border color by position via `nth-child(3n+...)`).
Still zero JavaScript — all via CSS custom properties, gradients, and
`color-mix()`.

**Information fix — Writing section only, fully real now**: fetched
Ali's actual Google Scholar profile
(`scholar.google.com/citations?user=0ibpiooAAAAJ`) and replaced the two
`PLACEHOLDER` entries in `data/writing.yaml` with 11 real publications
(titles, co-authors, venues, years, citation counts — GuideBeacon, 204
citations, down to GuideCall, 3). Linked each via a Google-Scholar
search-by-title URL rather than guessing a direct publisher link, except
the patent (linked directly to Google Patents). Updated
`layouts/writing/list.html` to render authors and citation counts too —
real, verifiable substance instead of placeholder text.

**Tried but did not use**: fetched Ali's LinkedIn profile
(`linkedin.com/in/sacheraghi`) for work-history details to fill the
Experience section the same way. Got a partial, fuzzy result (PhD at
Wichita State 2015-2019, Caterpillar Inc. as an employer, NSF I-Corps 2018,
1 patent — all consistent with the Scholar data) but **specific job
titles and dates were not reliably extracted** (LinkedIn scrapes are
known to be incomplete/truncated). Deliberately did not write this into
the site — wrong dates/titles on a job-search portfolio would be worse
than a placeholder. Asked Ali to confirm/provide the real details instead
of publishing a guess.

**Still open** (needs Ali, not something to guess at): About page bio
paragraph, Experience timeline (real employer/title/dates), real project
write-ups for the 3 Projects entries (or swapping in real projects from
his actual research — GuideBeacon/CityGuide/etc. are strong, verified
candidates), a real resume PDF, and "add real photos" from the color
question above (no images on the site at all currently).

## 2026-06-21 — Consolidated to 2 pages, added a logo, fixed wide-screen layout bug

Ali said the site "does not look professional" — specifically: his name
sat in a narrow column in the middle of the screen with huge empty space
on either side, he didn't want many separate pages, and he wanted a
"mindloop" logo on the main page with everything personal moved onto the
Contact page.

- **Confirmed the layout bug first** before fixing anything: screenshotted
  the homepage at 1920×1080. `--max-width: 960px` centered via `margin:
  0 auto` was the entire content column — correct on a laptop screen, but
  on a wide monitor it left large flat dead zones left and right with
  nothing in them. This was a real, reproducible bug, not a misreading.
- **Restructured navigation**: six pages (Home, About, Projects, Skills,
  Experience, Writing, Contact) collapsed to two (Home, Contact). Deleted
  `content/about/_index.md`, `content/skills/_index.md`,
  `content/experience/_index.md`, `content/writing/_index.md`,
  `content/projects/_index.md` (the standalone list page) — their
  underlying data (`data/skills.yaml`, `data/experience.yaml`,
  `data/writing.yaml`) and the individual project pages
  (`content/projects/<slug>.md`) were untouched and still feed the new
  consolidated Contact page. `hugo.toml`'s menu trimmed to a single
  "Contact" entry.
- **`/contact/` is now the real page**: bio, Skills grid, Projects grid
  (pulled via `where .Site.RegularPages "Section" "projects"` rather than
  depending on the now-deleted projects list page), Experience timeline +
  resume button, Writing list, and the actual contact links — all in one
  scrollable page with anchored sections (`#about`, `#skills`, etc.).
  Removed the now-orphaned list templates
  (`layouts/{skills,experience,writing,projects}/list.html`).
- **Home (`/`) became a minimal landing page**: logo + hero + one button
  ("View my work & get in touch →") linking to `/contact/`. No more
  About-teaser/Featured-Projects sections there — those live on Contact
  now.
- **Built a logo**: a hand-coded inline SVG (`layouts/partials/logo.html`)
  — an infinity-loop mark with a 4-stop gradient matching the site's
  accent palette (blue→purple→pink→amber), with a dark-mode override via
  an embedded `<style>` media query. Used in the header (next to the name)
  and bigger on the landing page. Had to parametrize the gradient's `id`
  (passed via `dict "id" "header"` / `dict "id" "landing"`) since the same
  partial is rendered twice on the homepage — without that, both usages
  would emit the same SVG element ID, which is invalid duplicate-ID HTML
  and would make the second reference silently resolve to the first
  gradient definition instead of its own.
- **Fixed the wide-screen layout bug**: bumped `--max-width` from 960px to
  1100px (modest, doesn't fully solve it alone), and — the actual fix —
  added a full-viewport, fixed-position, multi-color radial-gradient wash
  behind the whole page (`background-attachment: fixed`), so the area
  outside the content column is never flat/empty on any screen size, wide
  monitor or not.
- **Caught and fixed a self-inflicted bug while testing this**: after
  adding the full-bleed background, the hero's glow blobs (which have
  `overflow: hidden` on their parent `.hero` to clip them) rendered as a
  hard-edged dark rectangle behind the name — clipping that looked fine
  against the old flat background now looked like a floating box against
  the new colorful one. Fix: removed `overflow: hidden` from `.hero`
  (safe — it's now only used once, on the landing page, not clipped
  against other content) and added `overflow-x: hidden` to `body` instead,
  so the now-unclipped blobs can blend seamlessly without causing a
  horizontal scrollbar.
- Verified at 1920px, 1280px, and 390px (mobile) widths, and the full
  `/contact/` page end-to-end, via headless Chrome before pushing.
  Confirmed live on `mindsloop.org` after redeploy: logo renders, nav is
  just "Contact," `/about/` now correctly 404s (content moved, not
  duplicated), and the wide-screen background fills the viewport.

**Still open**: real bio, real Experience entries, real/expanded Projects,
resume PDF, and photos — same gaps as the previous entry, now living on a
single consolidated page instead of being spread across five.
