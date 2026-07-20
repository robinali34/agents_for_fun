#!/usr/bin/env python3
"""Collect a daily fitness log, analyze it with local Ollama, and save Markdown."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("FITNESS_DATA_ROOT", str(ROOT))).expanduser().resolve()
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = os.environ.get("FITNESS_MODEL", "qwen2.5:7b")


def ask(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{label}{suffix}: ").strip()
    return answer or default


def collect() -> dict[str, str]:
    print("\nDaily fat-loss log (leave blank if unknown)\n")
    return {
        "date": ask("Date", date.today().isoformat()),
        "weight_lb": ask("Morning weight (lb)"),
        "waist": ask("Waist (cm)"),
        "sleep": ask("Sleep duration / quality"),
        "steps": ask("Steps today"),
        "training": ask("Training (what + duration)"),
        "food": ask("Food overview"),
        "protein": ask("Protein (grams or food notes)"),
        "water": ask("Water intake"),
        "hunger": ask("Hunger 1-10"),
        "energy": ask("Energy / mood 1-10"),
        "pain": ask("Pain or discomfort (where + severity)"),
        "notes": ask("Other notes"),
    }


def make_prompt(data: dict[str, str]) -> str:
    values = "\n".join(f"- {key}: {value or 'not recorded'}" for key, value in data.items())
    return f"""You are a careful, practical fitness journaling assistant helping with sustainable fat loss.

From this single-day log, write a Markdown daily report:
{values}

Rules:
1. Output Markdown only — no code fences.
2. Keep the user's raw data; do not invent calories, macros, or body metrics.
3. Do not treat one-day weight change as fat loss/gain; weight is in pounds (lb). Say trend is insufficient without multi-day data.
4. Advice must be specific, gentle, and actionable — no extreme diets or punitive training.
5. If pain is non-zero or unusual, suggest reducing intensity; for chest pain, fainting, breathing trouble, or severe/persistent pain, clearly advise stopping and seeking medical care.
6. No medical diagnosis.

Use this structure:
# Fitness daily log｜{data['date']}
## Today's data
## Training & activity
## Food & recovery
## Analysis
## Suggestions for tomorrow
## Risks & cautions
## Raw notes
## Tags
"""


def analyze(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": "Respond in English."},
                {"role": "user", "content": prompt},
            ],
        }
    ).encode()
    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.load(response)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Cannot reach Ollama: {exc}") from exc
    return result["message"]["content"].strip()


def save(day: str, markdown: str) -> Path:
    year, month, _ = day.split("-")
    directory = DATA_ROOT / "daily" / year / month
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{day}.md"
    if destination.exists():
        answer = input(f"{destination} exists. Overwrite? [y/N]: ").strip().lower()
        if answer != "y":
            raise RuntimeError("Cancelled — file left unchanged")
    destination.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    return destination


def main() -> int:
    try:
        data = collect()
        print("\nAnalyzing with local model…")
        markdown = analyze(make_prompt(data))
        destination = save(data["date"], markdown)
        print(f"\nSaved: {destination}")
        return 0
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
