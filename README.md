# Ali Cheraghi — Portfolio Site

A Hugo static site, self-hosted on a home PC inside a dedicated VM for
isolation, served via Docker + Caddy, and exposed to the internet through
Cloudflare Tunnel (no port-forwarding). Full architecture/security rationale
is in [`PLAN.md`](./PLAN.md) — read that first if you want the "why."

## What's already scaffolded

- Hugo content/layout structure (`content/`, `layouts/`, `data/`) for the
  Hero, About, Projects, Skills, Experience, Writing, and Contact sections.
- Placeholder content for every section — three illustrative ML/CV/LLM
  project entries, placeholder experience/skills/writing data — clearly
  marked `PLACEHOLDER` for you to replace with real content.
- A minimal hand-written CSS theme (`static/css/main.css`) — no framework,
  no third-party Hugo theme, automatic dark mode, no client-side JS at all.
- `Dockerfile` (multi-stage: Hugo build → Caddy serve) and `Caddyfile`.
- Python rebuild automation under `deploy/rebuild/` (see "How it's built"
  below), plus systemd/cron unit files under `deploy/` as **text examples
  only** — nothing has been installed or enabled on this machine.

None of the following were done by this pass (deliberately — see
`PLAN.md`'s "scaffold-only" scope): no VM was created, no `hugo`/`docker`
were installed on this host, no domain was registered, no Cloudflare Tunnel
was configured, no git remote was pushed.

## Local preview — Hugo dev server

Requires Hugo installed locally (e.g. `sudo apt install hugo` on Debian/
Ubuntu, or grab a binary from https://gohugo.io/installation/).

```sh
hugo server -D
```

Open `http://localhost:1313`. `-D` includes draft content, useful while
placeholders are still being filled in (flip `draft: false` once a project
page is ready to publish).

## Local preview — via Docker

Requires Docker installed locally.

```sh
docker build -t mindloop-portfolio .
docker run --rm -p 8080:8080 mindloop-portfolio
```

Open `http://localhost:8080`. This builds the exact same image that would
run on the VM in production.

## Filling in real content

- Replace every `PLACEHOLDER` marker in `content/projects/*.md`,
  `data/experience.yaml`, `data/writing.yaml`, `content/about/_index.md`,
  and `content/contact/_index.md`.
- Add a real resume PDF at `static/resume.pdf` (delete
  `static/resume.pdf.placeholder.txt` once done) — the Experience page's
  "Download Resume" button already links to `/resume.pdf`.
- Add real project screenshots/GIFs under `static/images/` and reference
  them from the relevant project's front matter as a future enhancement.
- Use `hugo new projects/<slug>.md` to scaffold a new project page with
  pre-filled front matter (see `archetypes/projects.md`).

## Manual deployment steps (not done by this pass — your responsibility)

These need sudo/system access, interactive auth, or payment info that
weren't part of this implementation pass:

1. Install KVM/QEMU + `virt-manager`, create a dedicated VM (Debian/Ubuntu
   Server, 1 vCPU / 1GB RAM is plenty) for isolation from your main OS.
2. Snapshot the freshly-installed VM as a rollback point.
3. Inside the VM: install Docker, create a non-root user to run containers
   and the rebuild script.
4. Register a domain (Cloudflare Registrar recommended — at-cost, keeps
   DNS/Tunnel/Registrar in one place) and point its DNS to Cloudflare.
5. Create a public GitHub repo and push this project to it.
6. Clone that repo onto the VM at `/opt/mindloop` (or update `REPO_PATH` in
   `deploy/rebuild/main.py` if you use a different path).
7. Inside the VM: `docker build` + `docker run` per the commands above,
   confirm the container serves on `localhost:8080`.
8. Install and authenticate `cloudflared` inside the VM; create a tunnel
   pointing at `localhost:8080`.
9. Attach the domain to the tunnel in the Cloudflare dashboard; verify
   HTTPS end-to-end.
10. Install the rebuild automation: copy `deploy/mindloop-rebuild.service`
    and `.timer` into `/etc/systemd/system/`, then
    `systemctl enable --now mindloop-rebuild.timer` — or instead install
    the line from `deploy/mindloop-rebuild.cron.example` via `crontab -e`.
11. Harden the VM: default-deny firewall, unattended-upgrades, confirm no
    other inbound services (SSH, etc.) share the tunnel's network path.
12. Take a new VM snapshot once everything is verified working.

## How it's built — rebuild automation

`deploy/rebuild/` is a small Python program, not a monolithic shell
script — each class has exactly one job:

- `GitRepoUpdater` — fetch/compare/pull the content repo via git. Knows
  nothing about Docker or Hugo.
- `HugoSiteBuilder` — wraps a local `hugo` build. Not wired into the
  orchestrator (the Docker build stage already runs Hugo); kept as a clean
  standalone abstraction for local/non-Docker use.
- `DockerContainerManager` — owns the image build, stopping the old
  container, and starting the new one. Knows nothing about git or Hugo.
- `RebuildOrchestrator` — composes the two above: fetch → if the remote
  changed, pull + redeploy, else skip. The only class that knows the
  *sequence*; it never knows *how* git or Docker actually work.
- `main.py` — the sole entrypoint cron/systemd invokes
  (`python3 -m deploy.rebuild.main`); the only file with concrete paths,
  image/container names, and port numbers.

## Project structure reference

```
hugo.toml
archetypes/projects.md
content/        — Markdown content (Hero, About, Projects, Skills, ...)
data/           — structured YAML (skills, experience, writing)
layouts/        — Hugo templates + reusable partials
static/         — CSS, images, resume.pdf
Dockerfile      — multi-stage Hugo build → Caddy serve
Caddyfile       — serves the built static site on :8080
deploy/rebuild/ — Python rebuild automation (see above)
deploy/*.service, *.timer, *.cron.example — text examples, not installed
PLAN.md         — full architecture/security rationale
```

## Note on the old `index.html`

An earlier, abandoned plain HTML/CSS/JS scaffold (`index.html`) was removed
in favor of this Hugo-based structure, since the chosen content workflow is
Markdown-first and Hugo's content/layout separation gives real reuse
(e.g. the same `project-card` partial renders both the homepage's featured
projects and the full projects list) instead of one large hand-written file.
