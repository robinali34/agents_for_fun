# Local fitness log agent

Ask for a daily check-in, analyze with local Ollama, save Markdown.

## Dependencies

- Python 3.10+
- Ollama with model `qwen2.5:7b` (change `MODEL` in `fitness_agent.py` if needed)
- `curl` (launcher checks Ollama)

No extra pip packages.

## Run

```bash
cd ~/rli/agents_for_fun/agents/Fitness
./run.sh
```

Prompts cover weight (lb), waist, sleep, steps, training, food, protein, water,
hunger, energy, and pain, then generates a short analysis.

## Output

```text
daily/YYYY/MM/YYYY-MM-DD.md
```

Weekly folder reserved:

```text
weekly/
```

Personal logs are gitignored. For journaling and general tips only — not medical advice.
