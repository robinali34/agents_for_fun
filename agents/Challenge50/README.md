# 50-day challenge agent

Daily accountability log for a fixed **50-day** challenge. Uses local Ollama and saves Markdown.

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

Creates `challenge.json` (title, goal, start date) under the data root.

Day-to-day (recommended) use the AI_Data wrapper so journals stay outside git:

```bash
~/AI_Data/Challenge50/setup.sh
~/AI_Data/Challenge50/run.sh
~/AI_Data/Challenge50/status.sh
```

## Commands

```bash
./run.sh              # log today + LLM write-up
./run.sh status       # Day N/50, logged / missed counts
./run.sh setup        # create or replace challenge.json
./run.sh 2026-07-19   # backfill a date
```

## Prompts each day

- Did you do today’s action? (y / n / partial)
- What you did, optional minutes / energy / mood
- Blockers, one win, tomorrow intention

## Output

```text
daily/YYYY/MM/YYYY-MM-DD.md
challenge.json
```

Header includes `<!-- challenge50-day: N -->`.

## Env

| Variable | Meaning | Default |
|----------|---------|---------|
| `CHALLENGE50_DATA_ROOT` | Where journals + config live | agent folder |
| `CHALLENGE50_MODEL` | Ollama model | `qwen2.5:7b` |
| `AGENTS_FOR_FUN` | Repo root (wrappers) | `~/rli/agents_for_fun` |

For self-tracking only — not medical or professional advice.
