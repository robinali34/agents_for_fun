# 50-day challenge agent

Daily accountability log for a fixed **50-day** challenge with **multiple goals**. Uses local Ollama and saves Markdown.

## Dependencies

- Python 3.10+
- Ollama + `qwen2.5:7b` (override with `CHALLENGE50_MODEL`)
- `curl`, `bash`

No extra pip packages.

## First-time setup

```bash
cd ~/rli/agents_for_fun/agents/Challenge50
./setup.sh
```

Creates `challenge.json` (title, **goals list**, start date) under the data root.

Day-to-day (recommended) use the AI_Data wrapper so journals stay outside git:

```bash
~/AI_Data/Challenge50/setup.sh
~/AI_Data/Challenge50/run.sh
~/AI_Data/Challenge50/status.sh
```

## Commands

```bash
./run.sh              # log today (per-goal check-in) + LLM write-up
./run.sh status       # Day N/50 + goal list
./run.sh setup        # create / replace challenge, or edit goals
./run.sh goals        # list goals
./run.sh goals add    # add more goals
./run.sh goals pause 1
./run.sh goals resume g2
./run.sh 2026-07-19   # backfill a date
```

## Config shape

```json
{
  "title": "50-day challenge",
  "start_date": "2026-07-20",
  "total_days": 50,
  "goals": [
    {"id": "g1", "name": "Wake by 8am", "description": "Alarm + out of bed", "active": true},
    {"id": "g2", "name": "Walk 20 min", "description": "", "active": true}
  ]
}
```

Legacy single-field `"goal": "..."` is auto-upgraded to `goals[]` on load.

## Prompts each day

For **each active goal**:

- Done today? (y / n / partial)
- What you did, optional note

Then overall energy / mood / blockers / win / tomorrow.

## Output

```text
daily/YYYY/MM/YYYY-MM-DD.md
challenge.json
```

Header includes `<!-- challenge50-day: N goals: id1,id2 -->`.

## Env

| Variable | Meaning | Default |
|----------|---------|---------|
| `CHALLENGE50_DATA_ROOT` | Where journals + config live | agent folder |
| `CHALLENGE50_MODEL` | Ollama model | `qwen2.5:7b` |
| `AGENTS_FOR_FUN` | Repo root (wrappers) | `~/rli/agents_for_fun` |

For self-tracking only — not medical or professional advice.
