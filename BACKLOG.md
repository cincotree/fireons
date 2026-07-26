# Fireons Build Backlog

The backlog lives in [`backlog/`](backlog/), managed with the [Backlog.md](https://github.com/MrLesk/Backlog.md) CLI. Strategy and phasing live in [ROADMAP.md](ROADMAP.md).

Each task is one PR, with acceptance criteria as the definition of done. Milestones map to the roadmap build order:

| Milestone | Scope | Phase |
|---|---|---|
| A: Optional goal and progress | Goal model, progress UI, FIRE side calculator | 1 |
| B: Anonymity and session | Anonymous registration, handle-first display, session refresh | 1 |
| C: Professional directory | Professional model, browse/filter, profile and handoff, intake | 1 |
| D: Statement forwarding | Forwarding address, inbound receiving, inbox, PDF passwords | 1 |
| E: Site and launch | Truth pass, analytics, production launch | 1 |
| X: Horizontal foundations | CI, password reset, deletion/export, formatting, mobile, monitoring | 1 |
| L: DPDP and legal compliance | Consent, age gate, grievance, retention, nominee | 1 (L5 in 2) |
| F: Public journey pages | Public page, OG unfurl, amount toggle, paste-your-post | 2 |
| G: Automated statement parsing | CAS, banks, NRI brokerages | 2 |
| H: Public calculator suite | Time-to-goal, INR consolidation, two-country FI, return-to-India | 2 |

Common commands:

```bash
backlog board          # kanban in the terminal
backlog browser        # web UI
backlog task list --plain
backlog task edit task-1 -s "In Progress"
```

Suggested first tasks: X1 (CI), then A1 and B1 in parallel.
