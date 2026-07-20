#!/usr/bin/env python3
"""Build a local Tarot corpus from blog notes + public Pictorial Key data."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "corpus"
BLOG_POST = Path("/home/robina/rli/blog_book_notes/_posts/2026-04-28-rider-waite-1909-waite-tarot.md")
API_JSON = CORPUS_DIR / "tarot-api-cards.json"
OUT_JSON = CORPUS_DIR / "waite-rws.json"
OUT_INDEX = CORPUS_DIR / "index.md"

# Map English API names -> preferred Chinese names used by the agent.
EN_TO_ZH = {
    "The Fool": "愚者",
    "The Magician": "魔术师",
    "The High Priestess": "女祭司",
    "The Empress": "女皇",
    "The Emperor": "皇帝",
    "The Hierophant": "教皇",
    "The Lovers": "恋人",
    "The Chariot": "战车",
    "Strength": "力量",
    "The Hermit": "隐士",
    "Wheel of Fortune": "命运之轮",
    "Justice": "正义",
    "The Hanged Man": "倒吊人",
    "Death": "死神",
    "Temperance": "节制",
    "The Devil": "恶魔",
    "The Tower": "塔",
    "The Star": "星星",
    "The Moon": "月亮",
    "The Sun": "太阳",
    "Judgement": "审判",
    "The World": "世界",
    "Ace of Wands": "权杖一",
    "Two of Wands": "权杖二",
    "Three of Wands": "权杖三",
    "Four of Wands": "权杖四",
    "Five of Wands": "权杖五",
    "Six of Wands": "权杖六",
    "Seven of Wands": "权杖七",
    "Eight of Wands": "权杖八",
    "Nine of Wands": "权杖九",
    "Ten of Wands": "权杖十",
    "Page of Wands": "权杖侍从",
    "Knight of Wands": "权杖骑士",
    "Queen of Wands": "权杖皇后",
    "King of Wands": "权杖国王",
    "Ace of Cups": "圣杯一",
    "Two of Cups": "圣杯二",
    "Three of Cups": "圣杯三",
    "Four of Cups": "圣杯四",
    "Five of Cups": "圣杯五",
    "Six of Cups": "圣杯六",
    "Seven of Cups": "圣杯七",
    "Eight of Cups": "圣杯八",
    "Nine of Cups": "圣杯九",
    "Ten of Cups": "圣杯十",
    "Page of Cups": "圣杯侍从",
    "Knight of Cups": "圣杯骑士",
    "Queen of Cups": "圣杯皇后",
    "King of Cups": "圣杯国王",
    "Ace of Swords": "宝剑一",
    "Two of Swords": "宝剑二",
    "Three of Swords": "宝剑三",
    "Four of Swords": "宝剑四",
    "Five of Swords": "宝剑五",
    "Six of Swords": "宝剑六",
    "Seven of Swords": "宝剑七",
    "Eight of Swords": "宝剑八",
    "Nine of Swords": "宝剑九",
    "Ten of Swords": "宝剑十",
    "Page of Swords": "宝剑侍从",
    "Knight of Swords": "宝剑骑士",
    "Queen of Swords": "宝剑皇后",
    "King of Swords": "宝剑国王",
    "Ace of Pentacles": "星币一",
    "Two of Pentacles": "星币二",
    "Three of Pentacles": "星币三",
    "Four of Pentacles": "星币四",
    "Five of Pentacles": "星币五",
    "Six of Pentacles": "星币六",
    "Seven of Pentacles": "星币七",
    "Eight of Pentacles": "星币八",
    "Nine of Pentacles": "星币九",
    "Ten of Pentacles": "星币十",
    "Page of Pentacles": "星币侍从",
    "Knight of Pentacles": "星币骑士",
    "Queen of Pentacles": "星币皇后",
    "King of Pentacles": "星币国王",
}

ALIASES = {
    "愚人": "愚者",
    "圣杯王后": "圣杯皇后",
    "权杖王后": "权杖皇后",
    "宝剑王后": "宝剑皇后",
    "星币王后": "星币皇后",
    "钱币": "星币",
}


def normalize_heading_name(raw: str) -> tuple[str, str]:
    text = re.sub(r"<[^>]+>", "", raw).strip()
    text = re.sub(r"^[IVXLCDM0-9]+\s*[·\.]\s*", "", text)
    if "（" in text and "）" in text:
        zh, en = text.split("（", 1)
        return zh.strip(), en.replace("）", "").strip()
    if "·" in text:
        left, right = text.split("·", 1)
        left, right = left.strip(), right.strip()
        if re.search(r"[A-Za-z]", right):
            return left, right
        if re.search(r"[A-Za-z]", left):
            return right, left
        return left, right
    return text, ""


def parse_blog(path: Path) -> dict[str, dict[str, str]]:
    content = path.read_text(encoding="utf-8")
    headings = list(re.finditer(r"^(#{3,4})\s+(.+)$", content, re.M))
    cards: dict[str, dict[str, str]] = {}
    for index, heading in enumerate(headings):
        level = len(heading.group(1))
        title = heading.group(2).strip()
        end = len(content)
        for nxt in headings[index + 1 :]:
            if len(nxt.group(1)) <= level:
                end = nxt.start()
                break
        section = content[heading.start() : end]
        if "正位" not in section or "逆位" not in section:
            continue
        zh, en = normalize_heading_name(title)
        if zh in {"权杖", "圣杯", "宝剑", "星币"} or en in {"Wands", "Cups", "Swords", "Pentacles"}:
            continue
        if " " in zh and zh.split()[0] in {"权杖", "圣杯", "宝剑", "星币"} and len(zh.split()) == 2:
            # suit section titles like "圣杯 Cups"
            continue
        upright = ""
        reversed_ = ""
        m_up = re.search(r"<th[^>]*>正位</th>\s*<td>(.*?)</td>", section, re.S)
        m_rev = re.search(r"<th[^>]*>逆位</th>\s*<td>(.*?)</td>", section, re.S)
        if m_up:
            upright = re.sub(r"\s+", " ", m_up.group(1)).strip()
        if m_rev:
            reversed_ = re.sub(r"\s+", " ", m_rev.group(1)).strip()
        desc = ""
        m_desc = re.search(r"\*\*牌面描述\*\*\s*>\s*(.*?)(?:\n\n---|\n\n####|\n\n###|\Z)", section, re.S)
        if m_desc:
            desc = re.sub(r"\s+", " ", m_desc.group(1)).strip(" >")
        if not upright and not reversed_:
            continue
        key = zh or en
        cards[key] = {
            "name_zh": zh,
            "name_en": en,
            "upright_zh": upright,
            "reversed_zh": reversed_,
            "description_zh": desc,
            "source": str(path),
        }
    return cards


def load_api(path: Path) -> dict[str, dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cards: dict[str, dict[str, str]] = {}
    for item in data["cards"]:
        name_en = item["name"]
        name_zh = EN_TO_ZH.get(name_en, name_en)
        cards[name_zh] = {
            "name_zh": name_zh,
            "name_en": name_en,
            "name_short": item.get("name_short", ""),
            "type": item.get("type", ""),
            "value": item.get("value", ""),
            "upright_en": item.get("meaning_up", ""),
            "reversed_en": item.get("meaning_rev", ""),
            "description_en": item.get("desc", ""),
            "source": "https://github.com/ekelen/tarot-api",
        }
    return cards


def merge(blog: dict[str, dict[str, str]], api: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}
    for name_zh, item in api.items():
        merged[name_zh] = {
            **item,
            "aliases": [alias for alias, target in ALIASES.items() if target == name_zh],
        }
    for name_zh, item in blog.items():
        canonical = ALIASES.get(name_zh, name_zh)
        # Match by English if needed
        if canonical not in merged and item.get("name_en"):
            for key, value in list(merged.items()):
                if value.get("name_en") == item["name_en"]:
                    canonical = key
                    break
        base = merged.get(canonical, {"name_zh": canonical, "aliases": []})
        base.update(
            {
                "name_zh": canonical,
                "name_en": item.get("name_en") or base.get("name_en", ""),
                "upright_zh": item.get("upright_zh", ""),
                "reversed_zh": item.get("reversed_zh", ""),
                "description_zh": item.get("description_zh", ""),
                "blog_source": item.get("source", ""),
            }
        )
        aliases = set(base.get("aliases") or [])
        if name_zh != canonical:
            aliases.add(name_zh)
        base["aliases"] = sorted(aliases)
        merged[canonical] = base
    # Stable order: majors first roughly by known list, then others
    order = list(EN_TO_ZH.values())
    rank = {name: idx for idx, name in enumerate(order)}
    return [merged[name] for name in sorted(merged, key=lambda n: (rank.get(n, 999), n))]


def write_index(cards: list[dict[str, object]], path: Path) -> None:
    lines = [
        "# 本地塔罗语料索引",
        "",
        f"共 {len(cards)} 张牌。优先用于减少联网搜索与额外模型调用。",
        "",
        "| 中文 | English | 正位摘要 | 逆位摘要 |",
        "|------|---------|----------|----------|",
    ]
    for card in cards:
        up = str(card.get("upright_zh") or card.get("upright_en") or "")[:40]
        rev = str(card.get("reversed_zh") or card.get("reversed_en") or "")[:40]
        lines.append(
            f"| {card.get('name_zh','')} | {card.get('name_en','')} | {up} | {rev} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    if not API_JSON.exists():
        raise SystemExit(f"缺少 {API_JSON}，请先运行 ./fetch-corpus.sh")
    if not BLOG_POST.exists():
        raise SystemExit(f"缺少博客全牌解析：{BLOG_POST}")

    blog = parse_blog(BLOG_POST)
    api = load_api(API_JSON)
    cards = merge(blog, api)
    payload = {
        "version": 1,
        "card_count": len(cards),
        "sources": [
            str(BLOG_POST),
            "https://github.com/ekelen/tarot-api",
        ],
        "cards": cards,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_index(cards, OUT_INDEX)
    print(f"Wrote {OUT_JSON} ({len(cards)} cards)")
    print(f"Wrote {OUT_INDEX}")
    missing_zh = [c["name_zh"] for c in cards if not c.get("upright_zh")]
    if missing_zh:
        print(f"Warning: {len(missing_zh)} cards missing Chinese upright text")


if __name__ == "__main__":
    main()
