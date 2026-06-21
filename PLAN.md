# Portfolio Website — Architecture & Security Plan

## 1. Core Recommendation: Static Site Generator, Hosted on Home PC via Cloudflare Tunnel

**Decision (updated 2026-06-20): self-host from the home PC, using a static site generator and Cloudflare Tunnel.**

Rationale: a static site generator (Hugo or Next.js with static export) lets content be authored as Markdown files — project write-ups, learning posts — with no database and minimal maintenance. Cloudflare Tunnel removes the single biggest home-hosting risk (no port-forwarding, no inbound port ever opened on the router — the tunnel daemon makes an outbound-only connection to Cloudflare, which then routes public traffic to it). This makes home-hosting reasonable, but it is **not** structurally risk-free the way managed hosting (Cloudflare Pages/GitHub Pages) is — the home PC must stay powered on for uptime, and the guardrails below are **mandatory, not optional**, to keep "strangers cannot access files on my PC" true.

**Mandatory guardrails (non-negotiable for this architecture):**
- **Run everything inside a dedicated VM (KVM/QEMU via `virt-manager`, free, built into Linux) on the home PC — not directly on the host OS.** This gives a separate kernel and filesystem from your main machine, at zero hardware cost. The VM holds Docker, `cloudflared`, Caddy, and the rebuild cron job. If the website container were ever compromised, the blast radius stops at the VM boundary — there is no path from inside the VM to your host's personal files, SSH keys, browser profiles, or other documents. Resource footprint for a static site is trivial (1 vCPU / 512MB–1GB RAM is plenty).
- **Cloudflare Tunnel only, run from inside the VM** — never port-forward directly on the router, and never run `cloudflared` on the host.
- **Containerize the web server (Docker) inside the VM**: no bind-mounts of any directory outside the site's build output (no access to the VM's broader filesystem, let alone the host's).
- **Run the container as non-root**, with a **read-only filesystem mount** for the served content where possible.
- **No SSH or other services exposed** on the same host/network path as the tunnel — the tunnel should route only to the web container, and the VM itself should have no inbound listeners besides what's needed for you to manage it locally.
- **Reverse proxy with auto-TLS**: Caddy in front of the container, inside the VM (automatic HTTPS via Let's Encrypt).
- **Automatic OS + container base-image updates** inside the VM (unattended-upgrades for the VM's OS, Dependabot/Renovate for the Docker image) — and keep the host's hypervisor (KVM/QEMU) and OS patched too.
- **Snapshot the VM** after initial setup (a free KVM/QEMU feature) so it can be rolled back instantly if anything looks wrong.
- **fail2ban** is not strictly needed since no inbound port is open via the tunnel, but keep the VM's firewall default-deny anyway as defense in depth.

**Tradeoff to keep in mind:** if the home PC is off, asleep, or loses power/internet, the site goes down — unlike managed hosting where uptime is the provider's problem. Acceptable for a portfolio where occasional downtime isn't critical, but worth knowing going in.

## 2. Content Workflow

- Author each project or learning post as a **Markdown file** (Hugo content file or Next.js MDX page).
- Embed videos via YouTube embed (simplest, offloads bandwidth/storage to YouTube) or self-host video files if preferred — YouTube embed recommended to avoid serving large media from the home connection.
- Link out to Medium articles and papers directly (no need to mirror content).
- Pull in LinkedIn via a simple "View my LinkedIn" link/button — LinkedIn's API does not support embedding a live profile feed for individual developers, so a link is the standard practical approach.
- **Build + deploy automation**: push Markdown/content changes to GitHub → home PC rebuilds and redeploys. Since no inbound webhook should be exposed through the tunnel (keeps attack surface at zero), the simplest secure approach is the home PC **polling GitHub** on an interval (e.g. a cron job running `git pull` + rebuild every few minutes) rather than GitHub pushing a webhook to it. A self-hosted GitHub Actions runner on the home PC is a more "instant" alternative but adds complexity — start with polling, upgrade later only if needed.

## 3. Domain Name & HTTPS

- Register a custom domain (e.g. `.dev` reads well for engineers). Registrars: Cloudflare Registrar (at-cost, no markup, required if also using Cloudflare Tunnel/DNS) or Namecheap.
- Point the domain's DNS to Cloudflare (Cloudflare Tunnel requires the domain's DNS to be managed by Cloudflare).
- TLS is handled by Caddy (automatic HTTPS via Let's Encrypt) in front of the container, or via Cloudflare's edge TLS in front of the tunnel — effectively automatic either way, no manual certificate management.

## 4. Content Structure

1. **Hero** — name, title, one-liner
2. **About** — bio, years of experience, current focus areas
3. **Projects** — one Markdown page per project: problem, approach, tech stack, quantified results, embedded YouTube demo video, links to code/Medium articles/papers
4. **Skills** — Deep Learning, CV, LLMs/VLMs, Robotics/ROS2, MLOps tooling
5. **Experience/Resume** — timeline + downloadable PDF
6. **Writing** — list of Medium articles/papers (linked out, not mirrored)
7. **Contact** — email, LinkedIn (link), GitHub

## 5. Step-by-Step Action List

1. Install a hypervisor on the home PC if not already present (KVM/QEMU + `virt-manager` on Linux) and create a new VM (lightweight Linux distro, e.g. Debian/Ubuntu server) dedicated solely to this project.
2. Take a clean snapshot of the freshly-installed VM before installing anything else, as a rollback point.
3. Inside the VM: install Docker, set up a non-root user for running containers.
4. Decide on domain name; register it via Cloudflare Registrar (keeps DNS + Tunnel + Registrar in one place).
5. Move the domain's DNS to Cloudflare (automatic if registered there).
6. Create a public GitHub repo (e.g. `ali-portfolio`).
7. Scaffold the site with Hugo (or Next.js static export) — Markdown content for About/Projects/Writing.
8. Containerize: write a Dockerfile that builds the static site and serves it (e.g. via Caddy) with no bind-mounts outside the build output, running as non-root.
9. Install `cloudflared` (Cloudflare Tunnel daemon) **inside the VM**, authenticate it, and create a tunnel pointing at the local container's port.
10. Attach the custom domain to the tunnel in the Cloudflare dashboard; confirm HTTPS is active end-to-end.
11. Set up a cron job (or systemd timer) **inside the VM** that polls GitHub (`git pull`) on an interval and rebuilds/restarts the container on changes.
12. Harden the VM: enable a default-deny firewall, enable unattended OS updates, confirm no other services (SSH, etc.) share the tunnel's network path. Take a new snapshot once everything is working.
13. Build out content sections with real metrics, add SEO meta tags and Open Graph tags.
14. Test mobile/desktop, run a Lighthouse/accessibility pass.
15. Publish, add the live URL to LinkedIn/resume/GitHub profile.

## 6. Industry-Standard Tools

- **KVM/QEMU + `virt-manager`** — free, built-in Linux virtualization; isolates the whole stack (Docker, `cloudflared`, Caddy) in a separate kernel/filesystem from the host, at zero hardware cost. The standard way to get "separate machine" isolation without buying a separate machine.
- **Hugo** — static site generator, Markdown-based content, fast builds, minimal maintenance; good fit for "write Markdown, rebuild, done." Next.js is the alternative if richer custom React components are wanted later.
- **Cloudflare Tunnel (`cloudflared`)** — outbound-only connection from the VM to Cloudflare; eliminates port-forwarding and keeps the router's inbound ports closed.
- **Caddy** — reverse proxy with automatic TLS via Let's Encrypt, fronting the containerized site.
- **Docker** — isolates the web server process from the VM's filesystem; mandatory guardrail for this architecture, not optional.
- **cron / systemd timer** — simplest secure way to trigger rebuilds on GitHub changes without exposing a webhook endpoint through the tunnel.
- **Prettier/ESLint** — formatting/linting consistency for JS/TS if using Next.js.

## Open Decisions (last updated 2026-06-20)

1. Hosting: **self-hosted in a dedicated VM on the home PC, via Cloudflare Tunnel** (VM-based isolation added per security review; mandatory guardrails above apply).
2. Stack: leaning **Hugo** for Markdown-first simplicity — confirm, or choose Next.js if more custom UI is wanted.
3. Domain: TBD — needs registration via Cloudflare Registrar.
4. Rebuild automation: cron-based GitHub polling (simple, no exposed webhook) — confirm, or opt into a self-hosted GitHub Actions runner later for instant rebuilds.
5. VM specs/distro: TBD — recommend a minimal Debian or Ubuntu Server image, 1 vCPU / 1GB RAM as a starting point.
