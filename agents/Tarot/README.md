# Local Tarot agent

Generate daily / spread Markdown with local Ollama and a Rider–Waite–Smith corpus.  
UX ideas borrowed from [tarot-oracle](https://github.com/k98kurz/tarot-oracle), [2acrestudios/tarot](https://github.com/2acrestudios/tarot), and [arcanai](https://github.com/leahfrom/arcanai): **auto-draw**, **one-shot `-q`**, **confirm before LLM**.

## Dependencies

| Item | Purpose |
|------|---------|
| Python 3.10+ | Runtime |
| Ollama + `qwen2.5:7b` (configurable via `MODEL`) | Interpretation |
| `ddgs` | Optional web search (installed into `.venv` when needed) |
| Bundled `corpus/waite-rws.json` | Offline card meanings (78 cards) |
| Optional `TAROT_BLOG_POSTS` | Local Markdown excerpts (default `~/rli/blog_book_notes/_posts`) |

```bash
# optional explicit venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Quick start

```bash
cd ~/rli/agents_for_fun/agents/Tarot
# or from the original data path (recommended day-to-day):
#   cd ~/AI_Data/Tarot && ./tarot.sh
./fetch-corpus.sh
./tarot.sh
./tarot.sh 3 --draw -q "How should I plan next week?" -y --offline
```

Set `TAROT_DATA_ROOT` to keep Markdown journals outside the repo (the `~/AI_Data/Tarot` wrappers do this automatically).

Physical deck: omit `--draw` and type card names / upright-reversed by hand.

## Entry points

| Command | Role |
|---------|------|
| `./tarot.sh` | Unified menu / CLI |
| `./daily-one.sh` | Single-card daily |
| `./question-3.sh` | Situation / Obstacle / Advice |
| `./question-5.sh` | Five-card spread |
| `./fetch-corpus.sh` | Rebuild local corpus |

## Options

| Flag | Meaning |
|------|---------|
| `--draw` / `--auto` | Shuffle from 78 cards (with upright/reversed) |
| `-q` / `--question` | Question text |
| `--offline` | Skip web search |
| `-y` / `--yes` | Skip confirm / overwrite prompts |
| `--seed TEXT` | Reproducible draw |
| `YYYY-MM-DD` | Date override |

## Pipeline

```text
question / draw or manual cards
  → corpus resolve (fuzzy match; unknown names fail with suggestions)
  → confirm spread (skip with -y)
  → local corpus + optional web cache
  → per-card reading (spreads) or single-card write-up
  → save Markdown
```

## Save rules

- **Daily:** `YYYY/MM/YYYY-MM-DD.md`; different cards same day → `YYYY-MM-DD-HHMMSS.md`
- **Spreads:** `questions/YYYY/MM/YYYY-MM-DD-HHMMSS-{3|5}cards.md`
- Header fingerprint: `<!-- tarot-cards: ... -->`

## Notes

- Default model: `qwen2.5:7b` in `tarot_agent.py`
- For self-reflection only — not fate, medical, legal, or financial advice
- Non-romance questions try to avoid defaulting Cups cards into love readings
