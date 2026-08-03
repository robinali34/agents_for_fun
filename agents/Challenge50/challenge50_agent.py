#!/usr/bin/env python3
"""50-day challenge journal with multi-goal support (Ollama → Markdown)."""

from __future__ import annotations

import json
import os
import re
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


def slugify(text: str, fallback: str = "goal") -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text.strip().lower()).strip("-")
    return (slug[:32] or fallback)


def load_raw_config() -> dict[str, object]:
    if not CONFIG_PATH.exists():
        raise RuntimeError(
            f"Missing {CONFIG_PATH}\n"
            "Run ./setup.sh first to create your 50-day challenge."
        )
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def normalize_config(cfg: dict[str, object]) -> dict[str, object]:
    """Upgrade legacy single-goal configs to a goals list."""
    goals = cfg.get("goals")
    if isinstance(goals, list) and goals:
        normalized = []
        for index, item in enumerate(goals, 1):
            if isinstance(item, str):
                normalized.append(
                    {
                        "id": f"g{index}",
                        "name": item,
                        "description": "",
                        "active": True,
                    }
                )
                continue
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("title") or f"Goal {index}")
            normalized.append(
                {
                    "id": str(item.get("id") or f"g{index}-{slugify(name)}"),
                    "name": name,
                    "description": str(item.get("description") or item.get("detail") or ""),
                    "active": bool(item.get("active", True)),
                }
            )
        cfg["goals"] = normalized
    else:
        legacy = str(cfg.get("goal") or "").strip()
        if legacy:
            cfg["goals"] = [
                {
                    "id": "g1",
                    "name": legacy,
                    "description": "",
                    "active": True,
                }
            ]
        else:
            cfg["goals"] = []
    if "goal" not in cfg and cfg["goals"]:
        cfg["goal"] = " · ".join(g["name"] for g in cfg["goals"] if g.get("active"))
    return cfg


def load_config() -> dict[str, object]:
    return normalize_config(load_raw_config())


def save_config(cfg: dict[str, object]) -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    cfg = normalize_config(cfg)
    # Keep a flat summary field for older readers / quick glance.
    active = [g["name"] for g in cfg.get("goals", []) if isinstance(g, dict) and g.get("active")]
    cfg["goal"] = " · ".join(active)
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def active_goals(cfg: dict[str, object]) -> list[dict[str, object]]:
    return [g for g in cfg.get("goals", []) if isinstance(g, dict) and g.get("active")]


def collect_goals_interactive(existing: list[dict[str, object]] | None = None) -> list[dict[str, object]]:
    goals: list[dict[str, object]] = list(existing or [])
    if goals:
        print("\nCurrent goals:")
        for index, goal in enumerate(goals, 1):
            flag = "active" if goal.get("active") else "paused"
            print(f"  {index}. [{flag}] {goal.get('name')}")
        if ask("Keep existing goals and only add more?", "y").lower() in ("y", "yes", ""):
            pass
        else:
            goals = []

    print("\nAdd goals (empty name to finish). At least one goal is required.\n")
    while True:
        name = ask(f"Goal {len(goals) + 1} name")
        if not name:
            break
        description = ask("Description / daily action (optional)")
        goals.append(
            {
                "id": f"g{len(goals) + 1}-{slugify(name)}",
                "name": name,
                "description": description,
                "active": True,
            }
        )
    if not goals:
        raise RuntimeError("Need at least one goal")
    return goals


def setup() -> dict[str, object]:
    print("\n50-day challenge setup (multi-goal)\n")
    if CONFIG_PATH.exists():
        existing = load_config()
        print(f"Existing: {existing.get('title')} (start {existing.get('start_date')})")
        for goal in active_goals(existing):
            print(f"  · {goal.get('name')}")
        mode = ask("Replace all / edit goals only / cancel? [r/e/c]", "e").lower()
        if mode in ("c", "cancel", "n", "no"):
            return existing
        if mode in ("e", "edit"):
            existing["goals"] = collect_goals_interactive(active_goals(existing))
            save_config(existing)
            print(f"\nUpdated goals → {CONFIG_PATH}")
            return existing
    cfg = {
        "title": ask("Challenge title", "50-day challenge"),
        "start_date": ask("Start date (YYYY-MM-DD)", date.today().isoformat()),
        "total_days": TOTAL_DAYS,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "goals": collect_goals_interactive(),
    }
    date.fromisoformat(str(cfg["start_date"]))
    save_config(cfg)
    print(f"\nSaved config → {CONFIG_PATH}")
    return cfg


def cmd_goals_add() -> int:
    cfg = load_config()
    print("\nAdd goals (empty name to finish)\n")
    added = 0
    while True:
        name = ask(f"New goal name")
        if not name:
            break
        description = ask("Description / daily action (optional)")
        cfg.setdefault("goals", []).append(
            {
                "id": f"g{len(cfg['goals']) + 1}-{slugify(name)}",
                "name": name,
                "description": description,
                "active": True,
            }
        )
        added += 1
    if not added:
        print("No goals added.")
        return 0
    save_config(cfg)
    print(f"Added {added} goal(s) → {CONFIG_PATH}")
    return 0


def cmd_goals_list() -> int:
    cfg = load_config()
    goals = cfg.get("goals") or []
    print(f"\n{cfg.get('title')} — goals\n")
    if not goals:
        print("(none)")
        return 0
    for index, goal in enumerate(goals, 1):
        if not isinstance(goal, dict):
            continue
        flag = "active" if goal.get("active") else "paused"
        desc = f" — {goal.get('description')}" if goal.get("description") else ""
        print(f"{index}. [{flag}] {goal.get('id')}: {goal.get('name')}{desc}")
    return 0


def cmd_goals_pause(selector: str) -> int:
    cfg = load_config()
    goals = cfg.get("goals") or []
    hit = False
    for goal in goals:
        if not isinstance(goal, dict):
            continue
        if selector in (str(goal.get("id")), str(goal.get("name"))):
            goal["active"] = False
            hit = True
            print(f"Paused: {goal.get('name')}")
    if not hit:
        # allow 1-based index
        try:
            index = int(selector) - 1
            if 0 <= index < len(goals) and isinstance(goals[index], dict):
                goals[index]["active"] = False
                print(f"Paused: {goals[index].get('name')}")
                hit = True
        except ValueError:
            pass
    if not hit:
        raise RuntimeError(f"Goal not found: {selector}")
    save_config(cfg)
    return 0


def cmd_goals_resume(selector: str) -> int:
    cfg = load_config()
    goals = cfg.get("goals") or []
    hit = False
    for goal in goals:
        if not isinstance(goal, dict):
            continue
        if selector in (str(goal.get("id")), str(goal.get("name"))):
            goal["active"] = True
            hit = True
            print(f"Resumed: {goal.get('name')}")
    if not hit:
        try:
            index = int(selector) - 1
            if 0 <= index < len(goals) and isinstance(goals[index], dict):
                goals[index]["active"] = True
                print(f"Resumed: {goals[index].get('name')}")
                hit = True
        except ValueError:
            pass
    if not hit:
        raise RuntimeError(f"Goal not found: {selector}")
    save_config(cfg)
    return 0


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
        "missed_dates": missed[-10:],
        "missed_count": len(missed),
        "remaining_days": remaining,
        "in_window": current >= 1 and current <= total,
        "completed": current > total,
    }


def collect_goal_entries(goals: list[dict[str, object]]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    print("Per-goal check-in (y / n / partial)\n")
    for goal in goals:
        name = str(goal.get("name") or goal.get("id"))
        desc = str(goal.get("description") or "")
        print(f"→ {name}" + (f" ({desc})" if desc else ""))
        done = ask("  Done today? (y/n/partial)", "y")
        action = ask("  What did you do? (optional)")
        note = ask("  Note (optional)")
        entries.append(
            {
                "id": str(goal.get("id") or ""),
                "name": name,
                "description": desc,
                "done": done,
                "action": action,
                "note": note,
            }
        )
        print()
    return entries


def format_goal_block(entries: list[dict[str, str]]) -> str:
    lines = []
    for item in entries:
        lines.append(
            f"- {item['name']}: done={item['done'] or 'n/a'}; "
            f"action={item['action'] or '—'}; note={item['note'] or '—'}"
        )
    return "\n".join(lines) if lines else "(no active goals)"


def collect(cfg: dict[str, object], day: str) -> dict[str, object]:
    today = date.fromisoformat(day)
    prog = progress_summary(cfg, today)
    n = prog["day_number"]
    total = prog["total_days"]
    goals = active_goals(cfg)
    if not goals:
        raise RuntimeError("No active goals. Run ./setup.sh or: ./run.sh goals add")

    print(f"\n{cfg.get('title')} — Day {n}/{total}")
    print("Goals:")
    for goal in goals:
        desc = f" — {goal.get('description')}" if goal.get("description") else ""
        print(f"  · {goal.get('name')}{desc}")
    if prog["completed"]:
        print("Note: past day 50 — still logging as bonus day.")
    elif not prog["in_window"]:
        print("Note: before start date — check challenge.json start_date.")
    print(f"Logged so far: {prog['logged_count']} · Missed (before today): {prog['missed_count']}")
    print()

    goal_entries = collect_goal_entries(goals)
    done_yes = sum(1 for g in goal_entries if str(g["done"]).lower().startswith("y"))
    done_partial = sum(1 for g in goal_entries if "partial" in str(g["done"]).lower())
    done_no = len(goal_entries) - done_yes - done_partial

    return {
        "date": day,
        "day_number": str(n),
        "total_days": str(total),
        "title": str(cfg.get("title") or ""),
        "goals_summary": " · ".join(g["name"] for g in goals),
        "goals_detail": format_goal_block(goal_entries),
        "goals_json": json.dumps(goal_entries, ensure_ascii=False),
        "goals_done_yes": str(done_yes),
        "goals_done_partial": str(done_partial),
        "goals_done_no": str(done_no),
        "energy": ask("Overall energy 1-10 (optional)"),
        "mood": ask("Overall mood 1-10 (optional)"),
        "blockers": ask("Cross-goal blockers (optional)"),
        "win": ask("One win today (optional)"),
        "tomorrow": ask("Intention for tomorrow (optional)"),
        "notes": ask("Other notes (optional)"),
        "logged_count": str(prog["logged_count"]),
        "missed_count": str(prog["missed_count"]),
        "remaining_days": str(prog["remaining_days"]),
    }


def make_prompt(data: dict[str, object]) -> str:
    return f"""You are a practical accountability coach for a fixed-length multi-goal challenge.

Challenge: {data['title']}
Day: {data['day_number']} / {data['total_days']}
Date: {data['date']}
Active goals: {data['goals_summary']}

Per-goal results today:
{data['goals_detail']}

Counts: yes={data['goals_done_yes']}, partial={data['goals_done_partial']}, no={data['goals_done_no']}
Energy: {data.get('energy') or 'n/a'}
Mood: {data.get('mood') or 'n/a'}
Blockers: {data.get('blockers') or 'n/a'}
Win: {data.get('win') or 'n/a'}
Tomorrow intention: {data.get('tomorrow') or 'n/a'}
Notes: {data.get('notes') or 'n/a'}
Logged days so far: {data['logged_count']} · Missed before today: {data['missed_count']} · Remaining: {data['remaining_days']}

Rules:
1. Markdown only — no code fences.
2. Do not invent facts.
3. Cover EACH goal briefly in a table or bullet list (done status + note).
4. Encouraging but honest; no shame.
5. One small next step per incomplete goal (or one shared step if all done).

Structure:
# {data['title']}｜Day {data['day_number']}/{data['total_days']}｜{data['date']}
## Progress snapshot
## Goals today
(table or bullets: Goal | Status | What happened)
## What worked
## Friction
## Coach note
## Tomorrow
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


def save(day: str, day_number: str, markdown: str, goal_ids: list[str]) -> Path:
    year, month, _ = day.split("-")
    directory = DATA_ROOT / "daily" / year / month
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{day}.md"
    meta = f"<!-- challenge50-day: {day_number} goals: {','.join(goal_ids)} -->\n"
    body = meta + markdown.lstrip()
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
    print(f"Start: {cfg.get('start_date')}")
    print(f"Today: Day {prog['day_number']}/{prog['total_days']}")
    print(f"Logged entries: {prog['logged_count']}")
    print(f"Missed days (before today): {prog['missed_count']}")
    if prog["missed_dates"]:
        print("Recent misses: " + ", ".join(prog["missed_dates"]))
    print(f"Remaining (incl. today if in window): {prog['remaining_days']}")
    print("\nGoals:")
    goals = cfg.get("goals") or []
    if not goals:
        print("  (none — run ./setup.sh)")
    for goal in goals:
        if not isinstance(goal, dict):
            continue
        flag = "active" if goal.get("active") else "paused"
        desc = f" — {goal.get('description')}" if goal.get("description") else ""
        print(f"  [{flag}] {goal.get('name')}{desc}")
    print(f"\nConfig: {CONFIG_PATH}")
    print(f"Daily logs: {DATA_ROOT / 'daily'}")
    return 0


def cmd_log(day: str | None = None) -> int:
    cfg = load_config()
    day = day or date.today().isoformat()
    date.fromisoformat(day)
    data = collect(cfg, day)
    print("\nAnalyzing with local model…")
    markdown = analyze(make_prompt(data))
    goal_ids = [str(g.get("id") or "") for g in active_goals(cfg)]
    destination = save(day, str(data["day_number"]), markdown, goal_ids)
    print("\n" + "=" * 64)
    print(markdown)
    print("=" * 64)
    print(f"\nSaved: {destination}")
    return 0


def cmd_goals(argv: list[str]) -> int:
    if not argv:
        return cmd_goals_list()
    sub = argv[0]
    if sub == "list":
        return cmd_goals_list()
    if sub == "add":
        return cmd_goals_add()
    if sub == "pause" and len(argv) >= 2:
        return cmd_goals_pause(argv[1])
    if sub == "resume" and len(argv) >= 2:
        return cmd_goals_resume(argv[1])
    raise RuntimeError(
        "Usage: goals [list|add|pause <id|name|n>|resume <id|name|n>]"
    )


def main(argv: list[str]) -> int:
    try:
        args = [a for a in argv[1:] if not a.startswith("-")]
        flags = [a for a in argv[1:] if a.startswith("-")]
        if "--help" in flags or "-h" in flags:
            print(
                "Usage:\n"
                "  challenge50_agent.py setup\n"
                "  challenge50_agent.py status\n"
                "  challenge50_agent.py goals [list|add|pause X|resume X]\n"
                "  challenge50_agent.py [log] [YYYY-MM-DD]\n"
            )
            return 0
        cmd = args[0] if args else "log"
        if cmd == "setup":
            setup()
            return 0
        if cmd == "status":
            return cmd_status()
        if cmd == "goals":
            return cmd_goals(args[1:])
        if cmd == "log":
            day = args[1] if len(args) > 1 else None
            return cmd_log(day)
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
