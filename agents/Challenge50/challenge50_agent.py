#!/usr/bin/env python3
"""50-day challenge journal: log progress, analyze with Ollama, save Markdown."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("CHALLENGE50_DATA_ROOT", str(ROOT))).expanduser().resolve()
CONFIG_PATH = DATA_ROOT / "challenge.json"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = os.environ.get("CHALLENGE50_MODEL", "qwen2.5:7b")
TOTAL_DAYS = 50


def ask(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{label}{suffix}: ").strip()
    return answer or default


def load_config() -> dict[str, object]:
    if not CONFIG_PATH.exists():
        raise RuntimeError(
            f"Missing {CONFIG_PATH}\n"
            "Run ./setup.sh first to create your 50-day challenge."
        )
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(cfg: dict[str, object]) -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def setup() -> dict[str, object]:
    print("\n50-day challenge setup\n")
    if CONFIG_PATH.exists():
        existing = load_config()
        print(f"Existing challenge: {existing.get('title')} (start {existing.get('start_date')})")
        if ask("Replace it?", "n").lower() not in ("y", "yes"):
            return existing
    cfg = {
        "title": ask("Challenge title", "50-day challenge"),
        "goal": ask("Main goal (1–2 sentences)"),
        "start_date": ask("Start date (YYYY-MM-DD)", date.today().isoformat()),
        "total_days": TOTAL_DAYS,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    date.fromisoformat(str(cfg["start_date"]))
    save_config(cfg)
    print(f"\nSaved config → {CONFIG_PATH}")
    return cfg


def day_number(start: date, today: date) -> int:
    return (today - start).days + 1


def list_logged_days() -> list[date]:
    days: list[date] = []
    daily = DATA_ROOT / "daily"
    if not daily.is_dir():
        return days
    for path in daily.rglob("*.md"):
        try:
            days.append(date.fromisoformat(path.stem))
        except ValueError:
            continue
    return sorted(set(days))


def progress_summary(cfg: dict[str, object], today: date) -> dict[str, object]:
    start = date.fromisoformat(str(cfg["start_date"]))
    total = int(cfg.get("total_days") or TOTAL_DAYS)
    current = day_number(start, today)
    logged = list_logged_days()
    in_window = [d for d in logged if start <= d < start + timedelta(days=total)]
    done = min(max(current - 1, 0), total)  # days that should already have ended
    missed = []
    for offset in range(total):
        d = start + timedelta(days=offset)
        if d >= today:
            break
        if d not in in_window:
            missed.append(d.isoformat())
    remaining = max(total - current + 1, 0) if current <= total else 0
    return {
        "day_number": current,
        "total_days": total,
        "logged_count": len(in_window),
        "missed_dates": missed[-10:],  # last 10 misses only
        "missed_count": len(missed),
        "remaining_days": remaining,
        "in_window": current >= 1 and current <= total,
        "completed": current > total,
    }


def collect(cfg: dict[str, object], day: str) -> dict[str, object]:
    start = date.fromisoformat(str(cfg["start_date"]))
    today = date.fromisoformat(day)
    prog = progress_summary(cfg, today)
    n = prog["day_number"]
    total = prog["total_days"]

    print(f"\n{cfg.get('title')} — Day {n}/{total}")
    print(f"Goal: {cfg.get('goal') or '(not set)'}")
    if prog["completed"]:
        print("Note: past day 50 — still logging as bonus day.")
    elif not prog["in_window"]:
        print("Note: before start date — check challenge.json start_date.")
    print(f"Logged so far: {prog['logged_count']} · Missed (before today): {prog['missed_count']}")
    print()

    return {
        "date": day,
        "day_number": str(n),
        "total_days": str(total),
        "title": str(cfg.get("title") or ""),
        "goal": str(cfg.get("goal") or ""),
        "did_today": ask("Did you do today's challenge action? (y/n/partial)"),
        "action": ask("What did you do today?"),
        "minutes": ask("Minutes spent (optional)"),
        "energy": ask("Energy 1-10 (optional)"),
        "mood": ask("Mood 1-10 (optional)"),
        "blockers": ask("Blockers / friction (optional)"),
        "win": ask("One win today (optional)"),
        "tomorrow": ask("Intention for tomorrow (optional)"),
        "notes": ask("Other notes (optional)"),
        "logged_count": str(prog["logged_count"]),
        "missed_count": str(prog["missed_count"]),
        "remaining_days": str(prog["remaining_days"]),
    }


def make_prompt(data: dict[str, object]) -> str:
    values = "\n".join(f"- {k}: {v or 'not recorded'}" for k, v in data.items())
    return f"""You are a practical accountability coach for a fixed-length challenge.

Write a Markdown daily log from this data:
{values}

Rules:
1. Markdown only — no code fences.
2. Do not invent facts the user did not provide.
3. Be encouraging but honest; no shame for missed days.
4. Keep advice small and doable for tomorrow.
5. Mention Day N / {data['total_days']} clearly.

Structure:
# {data['title']}｜Day {data['day_number']}/{data['total_days']}｜{data['date']}
## Progress snapshot
## Today
## What worked
## Friction
## Coach note
## Tomorrow (one small step)
## Raw notes
## Tags
"""


def analyze(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": "Respond in English. Be concise and practical."},
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


def save(day: str, day_number: str, markdown: str) -> Path:
    year, month, _ = day.split("-")
    directory = DATA_ROOT / "daily" / year / month
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{day}.md"
    body = f"<!-- challenge50-day: {day_number} -->\n" + markdown.lstrip()
    if destination.exists():
        answer = input(f"{destination} exists. Overwrite? [y/N]: ").strip().lower()
        if answer != "y":
            raise RuntimeError("Cancelled — file left unchanged")
    destination.write_text(body.rstrip() + "\n", encoding="utf-8")
    return destination


def cmd_status() -> int:
    cfg = load_config()
    today = date.today()
    prog = progress_summary(cfg, today)
    print(f"\n{cfg.get('title')}")
    print(f"Goal: {cfg.get('goal') or '(not set)'}")
    print(f"Start: {cfg.get('start_date')}")
    print(f"Today: Day {prog['day_number']}/{prog['total_days']}")
    print(f"Logged entries: {prog['logged_count']}")
    print(f"Missed days (before today): {prog['missed_count']}")
    if prog["missed_dates"]:
        print("Recent misses: " + ", ".join(prog["missed_dates"]))
    print(f"Remaining (incl. today if in window): {prog['remaining_days']}")
    print(f"Config: {CONFIG_PATH}")
    print(f"Daily logs: {DATA_ROOT / 'daily'}")
    return 0


def cmd_log(day: str | None = None) -> int:
    cfg = load_config()
    day = day or date.today().isoformat()
    date.fromisoformat(day)
    data = collect(cfg, day)
    print("\nAnalyzing with local model…")
    markdown = analyze(make_prompt(data))
    destination = save(day, str(data["day_number"]), markdown)
    print("\n" + "=" * 64)
    print(markdown)
    print("=" * 64)
    print(f"\nSaved: {destination}")
    return 0


def main(argv: list[str]) -> int:
    try:
        args = [a for a in argv[1:] if not a.startswith("-")]
        flags = [a for a in argv[1:] if a.startswith("-")]
        if "--help" in flags or "-h" in flags:
            print(
                "Usage:\n"
                "  challenge50_agent.py setup\n"
                "  challenge50_agent.py status\n"
                "  challenge50_agent.py [log] [YYYY-MM-DD]\n"
            )
            return 0
        cmd = args[0] if args else "log"
        if cmd == "setup":
            setup()
            return 0
        if cmd == "status":
            return cmd_status()
        if cmd == "log":
            day = args[1] if len(args) > 1 else None
            return cmd_log(day)
        # bare date or default log
        if len(cmd) == 10 and cmd[4] == "-":
            return cmd_log(cmd)
        return cmd_log()
    except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled")
        return 130


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
