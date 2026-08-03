#!/usr/bin/env python3
"""Apple DFT workplace coach: generate plans with Ollama and always save Markdown."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("WORKPLACE_DATA_ROOT", str(ROOT))).expanduser().resolve()
PLANS_DIR = DATA_ROOT / "plans"
NOTES_DIR = DATA_ROOT / "notes"
INDEX_PATH = DATA_ROOT / "index.md"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = os.environ.get("WORKPLACE_MODEL", "qwen2.5:7b")

PLAN_KINDS = {
    "30": {
        "slug": "30day",
        "title": "First 30-day onboarding plan",
        "focus": "access, role clarity, relationships, one small win",
    },
    "60": {
        "slug": "60day",
        "title": "Days 31–60 deepening plan",
        "focus": "bounded ownership, dependency map, glossary, visible delivery",
    },
    "90": {
        "slug": "90day",
        "title": "Days 61–90 delivery plan",
        "focus": "improvement proposal, growth conversation, medium-term theme",
    },
    "weekly": {
        "slug": "weekly",
        "title": "Weekly focus plan",
        "focus": "shipped / learned / stuck / next-week top 3 / energy",
    },
    "learning": {
        "slug": "learning",
        "title": "DFT learning map for a software engineer",
        "focus": "scan/BIST/ATE concepts, SW leverage points, study cadence, questions for humans",
    },
    "1on1": {
        "slug": "1on1",
        "title": "Manager 1:1 prep",
        "focus": "updates, asks, risks, decisions needed",
    },
    "custom": {
        "slug": "custom",
        "title": "Custom workplace plan",
        "focus": "whatever the user describes",
    },
}


def ask(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{label}{suffix}: ").strip()
    return answer or default


def ensure_dirs() -> None:
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text.strip().lower()).strip("-")
    return (slug[:48] or "plan")


def analyze(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": MODEL,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Respond in English unless the user writes Chinese. "
                        "Output Markdown only — no code fences. "
                        "Never invent Apple-confidential process. "
                        "Prefer checklists and concrete asks for humans."
                    ),
                },
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


def make_plan_prompt(kind: str, day: str, context: dict[str, str]) -> str:
    meta = PLAN_KINDS[kind]
    extras = "\n".join(f"- {k}: {v or 'n/a'}" for k, v in context.items())
    return f"""You are a practical onboarding coach for a Senior Software Engineer joining Apple
in a Design-for-Test (DFT) for hardware context (software tooling / automation / test frameworks).

Create: {meta['title']}
Date: {day}
Focus areas: {meta['focus']}

User context:
{extras}

Rules:
1. Markdown only — no surrounding code fences.
2. Do not invent Apple-internal tools, orgs, or confidential process.
3. Include Goal, This period actions, Asks for humans, Risks, Optional deeper dive.
4. Keep it actionable for a senior IC.

Required structure:
# {meta['title']}｜{day}
## Goal
## Plan
## Asks for humans
## Risks & watch-outs
## Optional deeper dive
## Tags
"""


def plan_path(day: str, slug: str, label: str = "") -> Path:
    year, month, _ = day.split("-")
    directory = PLANS_DIR / year / month
    directory.mkdir(parents=True, exist_ok=True)
    extra = f"-{slugify(label)}" if label else ""
    return directory / f"{day}-{slug}{extra}.md"


def write_markdown(destination: Path, markdown: str, kind: str, day: str) -> Path:
    ensure_dirs()
    body = markdown.lstrip()
    if not body.startswith("---"):
        header = (
            "---\n"
            f"kind: {kind}\n"
            f"date: {day}\n"
            f"created_at: {datetime.now().isoformat(timespec='seconds')}\n"
            f"model: {MODEL}\n"
            "---\n\n"
        )
        body = header + body
    if destination.exists():
        answer = input(f"{destination} exists. Overwrite? [y/N]: ").strip().lower()
        if answer != "y":
            raise RuntimeError("Cancelled — file left unchanged")
    destination.write_text(body.rstrip() + "\n", encoding="utf-8")
    update_index(destination, kind, day)
    return destination


def update_index(path: Path, kind: str, day: str) -> None:
    ensure_dirs()
    rel = path.relative_to(DATA_ROOT).as_posix()
    line = f"| {day} | {kind} | [{path.name}](./{rel}) |"
    if not INDEX_PATH.exists():
        INDEX_PATH.write_text(
            "# Workplace plans index\n\n"
            "| Date | Kind | File |\n"
            "|------|------|------|\n"
            f"{line}\n",
            encoding="utf-8",
        )
        return
    text = INDEX_PATH.read_text(encoding="utf-8")
    if path.name in text and day in text:
        return
    if not text.endswith("\n"):
        text += "\n"
    INDEX_PATH.write_text(text + line + "\n", encoding="utf-8")


def collect_context(kind: str) -> dict[str, str]:
    print("\nContext (optional — Enter to skip)\n")
    ctx = {
        "start_date": ask("Job / team start date", date.today().isoformat()),
        "manager_focus": ask("What your manager emphasized so far"),
        "current_blockers": ask("Current blockers"),
        "energy": ask("Energy 1-10"),
    }
    if kind == "weekly":
        ctx["raw_week"] = ask("Raw dump of this week (shipped / stuck / notes)")
    elif kind == "1on1":
        ctx["meeting_goal"] = ask("Goal for this 1:1")
        ctx["updates"] = ask("Updates to share")
    elif kind == "custom":
        ctx["request"] = ask("What plan do you need?")
    else:
        ctx["notes"] = ask("Anything else the plan should reflect")
    return ctx


def cmd_plan(kind: str | None = None, day: str | None = None) -> int:
    ensure_dirs()
    day = day or date.today().isoformat()
    date.fromisoformat(day)
    if not kind:
        print("Plan kinds: " + ", ".join(PLAN_KINDS))
        kind = ask("Kind", "30").lower()
    if kind in ("30day", "30-day", "first30"):
        kind = "30"
    if kind in ("60day", "60-day"):
        kind = "60"
    if kind in ("90day", "90-day"):
        kind = "90"
    if kind not in PLAN_KINDS:
        raise RuntimeError(f"Unknown kind '{kind}'. Choose: {', '.join(PLAN_KINDS)}")

    context = collect_context(kind)
    label = ""
    if kind == "custom":
        label = context.get("request") or "custom"

    print("\nGenerating plan with local model…")
    markdown = analyze(make_plan_prompt(kind, day, context))
    destination = plan_path(day, PLAN_KINDS[kind]["slug"], label)
    saved = write_markdown(destination, markdown, kind, day)

    print("\n" + "=" * 64)
    print(markdown)
    print("=" * 64)
    print(f"\nSaved: {saved}")
    return 0


def cmd_save(day: str | None = None, kind: str = "custom") -> int:
    """Save Markdown from stdin (e.g. paste from Dify) to plans/."""
    ensure_dirs()
    day = day or date.today().isoformat()
    date.fromisoformat(day)
    if kind not in PLAN_KINDS:
        kind = "custom"
    print("Paste Markdown plan, then Ctrl-D (Linux) / Ctrl-Z Enter (Windows) when done:\n")
    markdown = sys.stdin.read().strip()
    if not markdown:
        raise RuntimeError("No Markdown received on stdin")
    label = ask("Short label for filename (optional)", kind)
    destination = plan_path(day, PLAN_KINDS[kind]["slug"], label if label != kind else "")
    saved = write_markdown(destination, markdown, kind, day)
    print(f"\nSaved: {saved}")
    return 0


def cmd_list() -> int:
    ensure_dirs()
    files = sorted(PLANS_DIR.rglob("*.md"))
    if not files:
        print(f"No plans yet under {PLANS_DIR}")
        return 0
    print(f"Plans in {PLANS_DIR}:\n")
    for path in files:
        print(f"  {path.relative_to(DATA_ROOT)}")
    if INDEX_PATH.exists():
        print(f"\nIndex: {INDEX_PATH}")
    return 0


def main(argv: list[str]) -> int:
    try:
        args = [a for a in argv[1:] if not a.startswith("-")]
        flags = [a for a in argv[1:] if a.startswith("-")]
        if "--help" in flags or "-h" in flags:
            print(
                "Usage:\n"
                "  workplace_agent.py plan [30|60|90|weekly|learning|1on1|custom] [YYYY-MM-DD]\n"
                "  workplace_agent.py save [kind] [YYYY-MM-DD]   # read Markdown from stdin\n"
                "  workplace_agent.py list\n"
            )
            return 0
        cmd = args[0] if args else "plan"
        if cmd == "list":
            return cmd_list()
        if cmd == "save":
            kind = args[1] if len(args) > 1 and args[1] in PLAN_KINDS else "custom"
            day = None
            for item in args[1:]:
                if len(item) == 10 and item[4] == "-":
                    day = item
            return cmd_save(day=day, kind=kind)
        if cmd == "plan":
            kind = args[1] if len(args) > 1 else None
            day = args[2] if len(args) > 2 else None
            if kind and len(kind) == 10 and kind[4] == "-":
                day, kind = kind, None
            return cmd_plan(kind=kind, day=day)
        # bare kind
        if cmd in PLAN_KINDS or cmd in ("30day", "60day", "90day"):
            day = args[1] if len(args) > 1 else None
            return cmd_plan(kind=cmd, day=day)
        return cmd_plan()
    except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled")
        return 130


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
