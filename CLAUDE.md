# Request logging (applies to every agent working in this project)

Every agent that works in this project — including any agent created later —
must keep a running log of the user's last 10 requests *to that specific
agent*, so a future "what was the last ask?" can be answered by reading the
log instead of reconstructing intent from repo state.

**Where:** `.claude/agent-memory/<agent-name>/request_log.md` (create the
agent's `agent-memory/<agent-name>/` directory if it doesn't exist yet).

**Format:**

```markdown
---
name: request-log
description: Last 10 user requests made to this agent in this project
metadata:
  type: project
---

- 2026-06-20: <one-line summary of the ask>
- 2026-06-20: <one-line summary of the ask>
```

**Rules:**
- On receiving a new request, append one entry (date + concise summary of
  what was asked — not what was done) to the bottom of the list.
- Keep only the most recent 10 entries — drop the oldest when adding an
  11th.
- If the agent has its own `MEMORY.md` index (per the standard agent-memory
  convention), add/keep one line pointing to `request_log.md`.
- This log is separate from other project-state memory (e.g.
  `project_state.md`) — it tracks *what was asked*, not architecture
  decisions or build status.

# Project history log (applies to every agent working in this project)

Every agent that works in this project — including any agent created later
— must record significant actions taken into a single shared history file
at the project root: **`history.md`**.

**Rules:**
- Append a dated section (or bullet under the current date's section) for
  each significant piece of work: what was done, key commands/decisions,
  and the resulting state. Write it so someone with no other context could
  reconstruct what happened and why.
- This is a **full, uncapped history** (unlike the per-agent
  `request_log.md` above, which only keeps the last 10 asks) — it's the
  project's running changelog, not a recent-activity buffer.
- Append-only in spirit: don't delete past entries to "clean up"; if
  something described earlier turns out to be wrong/superseded, add a new
  entry noting the correction rather than rewriting history.
- This is shared across all agents in the project (one `history.md`, not
  one per agent) — distinct from each agent's own `request_log.md` /
  `project_state.md` under `.claude/agent-memory/<agent-name>/`.
