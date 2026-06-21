# Ali Cheraghi — Portfolio Site

A Hugo static site, self-hosted on a home PC inside a dedicated VM for
isolation, served via Docker + Caddy, and exposed to the internet through
Cloudflare Tunnel (no port-forwarding). Full architecture/security rationale
is in [`PLAN.md`](./PLAN.md) — read that first if you want the "why."

**Status: live** at https://mindsloop.org and https://www.mindsloop.org.
Deployment is done — see [`history.md`](./history.md) for exactly what was
done and how. If you're looking for what to do when your computer restarts
or the site seems down, jump to ["If your computer restarts, or the site
goes down"](#if-your-computer-restarts-or-the-site-goes-down) below.

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

(The above was scaffolded in an earlier pass before any infrastructure
existed. All the infrastructure — VM, Docker, domain, Cloudflare Tunnel,
GitHub — has since been built; see "Deployment status" below.)

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

## Deployment status: done

All of the steps that used to be listed here as manual TODOs — VM creation,
Docker, the GitHub repo, the domain, the Cloudflare Tunnel, the rebuild
timer, firewall/auto-updates — are complete. The VM (`mindloop-vm`) is
running on the home PC, the site is live, and it redeploys itself on every
`git push` to `main` within about 5 minutes.

For exactly what was done, in what order, and the problems hit along the
way (stale group permissions, sudo quirks, DNS propagation, etc.), see
[`history.md`](./history.md) — it's the full step-by-step record. The
sections below cover what you'd actually need day-to-day: making content
changes, and what happens if the machine restarts or the site goes down.

## If your computer restarts, or the site goes down

Think of it like this: your real computer is a big house. Inside the
house, there's a smaller pretend-computer living inside it — that's the
**VM** (`mindloop-vm`). The website actually lives inside that pretend
computer, kind of like a toy house inside your real house.

**The good news: almost everything wakes itself back up, like a
wind-up toy.** You don't need to do anything most of the time. Here's the
order it happens in, all by itself:

1. Your real computer turns on.
2. A program called `libvirtd` wakes up automatically and says "time to
   turn on the pretend computer" — so the VM (`mindloop-vm`) turns itself
   on too, with no one touching anything.
3. Inside the VM, several little helper programs are all set to "turn on
   by yourself when the VM starts" — Docker, the secret tunnel to the
   internet (`cloudflared`), the firewall (`ufw`), the auto-update checker,
   and the rebuild checker. They all switch on by themselves.
4. The website itself lives inside a box called a **container**. That box
   is told "if you ever get turned off, turn yourself back on" — so it
   does, without anyone asking it to.

So: if your computer restarts (power went out, you rebooted it, anything
like that), just **wait about 1-2 minutes**, then check the website at
https://mindsloop.org in a browser. It should just be there.

### If it's NOT back after a few minutes — a simple checklist

Open a terminal on your real computer and go through these in order. Each
one checks one toy in the chain to see which one didn't wake up.

**1. Is the pretend computer (the VM) awake?**
```sh
sg libvirt -c "virsh list --all"
```
You want to see `mindloop-vm` with state `running`. If it says
`shut off` instead, wake it up yourself:
```sh
sg libvirt -c "virsh start mindloop-vm"
```

**2. Is the website's toy box (the container) turned on inside the VM?**
```sh
ssh mindloop2026ali@192.168.122.104 "docker ps --filter name=mindloop-portfolio"
```
You want to see `mindloop-portfolio` with status `Up ...`. If nothing
shows up, Docker itself may not have started — check with
`systemctl is-active docker` (over the same SSH connection), and if it's
not active: `sudo systemctl start docker` (you may need to type your VM
password for this one).

**3. Is the secret tunnel to the internet open?**
```sh
ssh mindloop2026ali@192.168.122.104 "systemctl is-active cloudflared"
```
You want to see `active`. If not: `sudo systemctl start cloudflared`.

**4. Still stuck?** There's a rollback button — three saved "snapshots" of
the VM from when everything was known to be working
(`pristine-install`, `working-baseline`, `public-live`). Worst case, you
can rewind the whole VM back to the last good one:
```sh
sg libvirt -c "virsh snapshot-revert mindloop-vm public-live"
```

### Why this works (the slightly more technical version)

- The VM has its **autostart flag turned on** (`virsh autostart
  mindloop-vm`), which is what makes step 2 above happen automatically.
  This was actually missing at first and got fixed on 2026-06-21 — see
  `history.md` for that story.
- Inside the VM, `docker`, `cloudflared`, `mindloop-rebuild.timer`, `ufw`,
  and `unattended-upgrades` are all `systemctl enable`d, which is what
  makes a service start by itself every time the VM boots.
- The website's container was started with `--restart unless-stopped`,
  which is Docker's own way of saying "bring this back automatically,
  no matter what, unless someone deliberately stopped it."

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
