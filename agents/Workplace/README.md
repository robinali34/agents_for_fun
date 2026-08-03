# Workplace agent — Apple DFT onboarding plans → Markdown

Local Ollama coach for settling into a **Senior SWE · Design-for-Test (hardware)** role.
Unlike the Dify Chatflow preview, **this agent always writes plans to disk**.

## Quick start

```bash
# Recommended (journals outside git):
~/AI_Data/Workplace/AppleDFT/run.sh plan 30

# Or from this folder (set data root first):
export WORKPLACE_DATA_ROOT=~/AI_Data/Workplace/AppleDFT
./run.sh plan 30
./run.sh plan weekly
./run.sh plan learning
./run.sh list
```

## Save a plan from Dify

If you generated a plan in Dify Preview, pipe or paste it:

```bash
~/AI_Data/Workplace/AppleDFT/run.sh save 30
# paste Markdown, then Ctrl-D
```

Or:

```bash
xclip -o -selection clipboard | ~/AI_Data/Workplace/AppleDFT/run.sh save weekly
```

## Output layout

```text
~/AI_Data/Workplace/AppleDFT/
├── plans/YYYY/MM/YYYY-MM-DD-30day.md
├── plans/YYYY/MM/YYYY-MM-DD-weekly.md
├── notes/                 # your private notes
├── knowledge/             # onboarding docs (also used by Dify KB)
├── index.md               # auto-updated index
└── run.sh
```

## Env

| Variable | Meaning | Default |
|----------|---------|---------|
| `WORKPLACE_DATA_ROOT` | Where plans + notes live | agent folder |
| `WORKPLACE_MODEL` | Ollama model | `qwen2.5:7b` |

## Dify companion

Browser Chatflow (chat only): `infra/dify/apps/apple-dft-onboarding/`  
For **files on disk**, use this agent.

Privacy: do not paste Apple-confidential material into plans.
