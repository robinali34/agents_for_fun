#!/usr/bin/env python3
"""每日一抽：本地语料 → 网络+cache → 校验 → 生成 Markdown。"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:7b"
BLOG_POSTS = Path("/home/robina/rli/blog_book_notes/_posts")
CORPUS_PATH = ROOT / "corpus" / "waite-rws.json"
_CORPUS_CACHE: dict[str, object] | None = None


def ensure_venv_python(need_web: bool = False) -> None:
    """Re-exec under Tarot/.venv when available / required for web search."""
    if os.environ.get("TAROT_VENV_ACTIVE") == "1":
        return
    if need_web:
        try:
            import ddgs  # noqa: F401
            return
        except ImportError:
            pass
        if not VENV_PYTHON.exists():
            raise RuntimeError(
                "联网搜索需要虚拟环境。请先运行：./fetch-corpus.sh 与 ./daily-one.sh\n"
                "或：python3 -m venv .venv && .venv/bin/pip install ddgs"
            )
        os.environ["TAROT_VENV_ACTIVE"] = "1"
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
        return
    # Offline path: prefer venv if present, otherwise continue on system Python.
    if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
        os.environ["TAROT_VENV_ACTIVE"] = "1"
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

CARD_ALIASES = {
    "six of wand": "权杖六",
    "six of wands": "权杖六",
    "6 of wands": "权杖六",
    "6 of wand": "权杖六",
    "愚人": "愚者",
    "圣杯王后": "圣杯皇后",
}


def ask(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def chat(messages: list[dict[str, str]], temperature: float = 0.3) -> str:
    body = json.dumps(
        {
            "model": MODEL,
            "stream": False,
            "options": {"temperature": temperature},
            "messages": messages,
        }
    ).encode()
    request = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.load(response)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"无法连接 Ollama：{exc}") from exc
    return result["message"]["content"].strip()


def collect(
    day: str,
    *,
    draw: bool = False,
    question: str | None = None,
    seed: str | None = None,
) -> dict[str, str]:
    print("\n每日一抽\n")
    if draw:
        from deck import draw_cards, format_drawn

        drawn = draw_cards(1, seed=seed)[0]
        print("自动抽牌：")
        print(format_drawn([drawn]))
        card = drawn["card_zh"]
        orientation = drawn["orientation"]
        q = question if question is not None else ask("今日问题（可选）")
        notes = "" if question is not None else ask("补充记录（可选）")
        return {
            "date": day,
            "card": card,
            "orientation": orientation,
            "question": q,
            "notes": notes,
            "drawn": "1",
        }

    card = ask("牌名")
    orientation = ask("正/逆")
    if not card or not orientation:
        raise RuntimeError("牌名和正/逆都必须填写")
    return {
        "date": day,
        "card": card,
        "orientation": orientation,
        "question": question if question is not None else ask("今日问题（可选）"),
        "notes": "" if question is not None else ask("补充记录（可选）"),
    }


def normalize_card(card: str) -> str:
    key = re.sub(r"\s+", " ", card.strip().lower())
    if key in CARD_ALIASES:
        return CARD_ALIASES[key]
    text = card.strip()
    return CARD_ALIASES.get(text, text)


def load_corpus() -> dict[str, object]:
    global _CORPUS_CACHE
    if _CORPUS_CACHE is not None:
        return _CORPUS_CACHE
    if not CORPUS_PATH.exists():
        raise RuntimeError(
            f"缺少本地语料 {CORPUS_PATH}\n请先运行：./fetch-corpus.sh"
        )
    _CORPUS_CACHE = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    return _CORPUS_CACHE


def lookup_corpus_card(card: str) -> dict[str, object] | None:
    corpus = load_corpus()
    needle = normalize_card(card)
    needle_l = needle.lower()
    for item in corpus.get("cards", []):
        names = {
            str(item.get("name_zh") or ""),
            str(item.get("name_en") or ""),
            *[str(alias) for alias in item.get("aliases") or []],
        }
        if needle in names or needle_l in {n.lower() for n in names if n}:
            return item
        # English fuzzy: "six of wand" vs "Six of Wands"
        en = str(item.get("name_en") or "").lower()
        if needle_l and en and (needle_l == en or needle_l.rstrip("s") == en.rstrip("s")):
            return item
    return None


def format_corpus_card(card: dict[str, object], orientation: str) -> str:
    is_rev = "逆" in orientation
    upright = card.get("upright_zh") or card.get("upright_en") or ""
    reversed_ = card.get("reversed_zh") or card.get("reversed_en") or ""
    desc = card.get("description_zh") or card.get("description_en") or ""
    focus = reversed_ if is_rev else upright
    return (
        f"牌名：{card.get('name_zh')} / {card.get('name_en')}\n"
        f"当前朝向：{orientation}\n"
        f"本朝向牌义：{focus}\n"
        f"正位：{upright}\n"
        f"逆位：{reversed_}\n"
        f"牌面：{desc}\n"
        f"来源：本地语料 corpus/waite-rws.json"
        + (f"；博客 {card.get('blog_source')}" if card.get("blog_source") else "")
    )


def resolve_card_plan(data: dict[str, str], *, require_corpus: bool = True) -> dict[str, object]:
    """Resolve card metadata from local corpus without an LLM call."""
    from deck import fuzzy_lookup, suggest_cards

    card = fuzzy_lookup(data["card"]) or lookup_corpus_card(data["card"])
    orientation = data["orientation"].strip()
    if orientation not in ("正", "逆", "正位", "逆位") and orientation:
        # tolerate "upright"/"reversed"
        if orientation.lower().startswith("rev") or "逆" in orientation:
            orientation = "逆位"
        elif orientation.lower().startswith("up") or "正" in orientation:
            orientation = "正位"
    orientation_full = "逆位" if "逆" in orientation else "正位"
    if not card:
        tips = suggest_cards(data["card"])
        tip_text = "；候选：" + "、".join(tips) if tips else ""
        if require_corpus:
            raise RuntimeError(f"未识别牌名「{data['card']}」{tip_text}")
        card_zh = normalize_card(data["card"])
        card_en = english_card_name(card_zh, data["card"])
    else:
        card_zh = str(card.get("name_zh") or normalize_card(data["card"]))
        card_en = str(card.get("name_en") or english_card_name(card_zh, data["card"]))
    orientation_en = "reversed" if "逆" in orientation_full else "upright"
    return {
        "card_zh": card_zh,
        "card_en": card_en,
        "orientation": orientation_full,
        "keywords": [
            f"{card_zh}{orientation_full}含义",
            f"{card_zh} {orientation_full} 塔罗 解读",
            f"{card_en} {orientation_en} meaning",
            f"{card_en} tarot {orientation_en}",
        ],
        "corpus_card": card,
    }


# Common English names for Chinese major/minor cards used in bilingual search.
CARD_EN = {
    "愚者": "The Fool",
    "愚人": "The Fool",
    "魔术师": "The Magician",
    "女祭司": "The High Priestess",
    "女皇": "The Empress",
    "皇帝": "The Emperor",
    "教皇": "The Hierophant",
    "恋人": "The Lovers",
    "战车": "The Chariot",
    "力量": "Strength",
    "隐士": "The Hermit",
    "命运之轮": "Wheel of Fortune",
    "正义": "Justice",
    "倒吊人": "The Hanged Man",
    "死神": "Death",
    "节制": "Temperance",
    "恶魔": "The Devil",
    "塔": "The Tower",
    "星星": "The Star",
    "月亮": "The Moon",
    "太阳": "The Sun",
    "审判": "Judgement",
    "世界": "The World",
    "权杖一": "Ace of Wands",
    "权杖二": "Two of Wands",
    "权杖三": "Three of Wands",
    "权杖四": "Four of Wands",
    "权杖五": "Five of Wands",
    "权杖六": "Six of Wands",
    "权杖七": "Seven of Wands",
    "权杖八": "Eight of Wands",
    "权杖九": "Nine of Wands",
    "权杖十": "Ten of Wands",
    "权杖侍从": "Page of Wands",
    "权杖骑士": "Knight of Wands",
    "权杖王后": "Queen of Wands",
    "权杖皇后": "Queen of Wands",
    "权杖国王": "King of Wands",
    "圣杯一": "Ace of Cups",
    "圣杯二": "Two of Cups",
    "圣杯三": "Three of Cups",
    "圣杯四": "Four of Cups",
    "圣杯五": "Five of Cups",
    "圣杯六": "Six of Cups",
    "圣杯七": "Seven of Cups",
    "圣杯八": "Eight of Cups",
    "圣杯九": "Nine of Cups",
    "圣杯十": "Ten of Cups",
    "圣杯侍从": "Page of Cups",
    "圣杯骑士": "Knight of Cups",
    "圣杯王后": "Queen of Cups",
    "圣杯皇后": "Queen of Cups",
    "圣杯国王": "King of Cups",
    "宝剑一": "Ace of Swords",
    "宝剑二": "Two of Swords",
    "宝剑三": "Three of Swords",
    "宝剑四": "Four of Swords",
    "宝剑五": "Five of Swords",
    "宝剑六": "Six of Swords",
    "宝剑七": "Seven of Swords",
    "宝剑八": "Eight of Swords",
    "宝剑九": "Nine of Swords",
    "宝剑十": "Ten of Swords",
    "宝剑侍从": "Page of Swords",
    "宝剑骑士": "Knight of Swords",
    "宝剑王后": "Queen of Swords",
    "宝剑皇后": "Queen of Swords",
    "宝剑国王": "King of Swords",
    "星币一": "Ace of Pentacles",
    "星币二": "Two of Pentacles",
    "星币三": "Three of Pentacles",
    "星币四": "Four of Pentacles",
    "星币五": "Five of Pentacles",
    "星币六": "Six of Pentacles",
    "星币七": "Seven of Pentacles",
    "星币八": "Eight of Pentacles",
    "星币九": "Nine of Pentacles",
    "星币十": "Ten of Pentacles",
    "星币侍从": "Page of Pentacles",
    "星币骑士": "Knight of Pentacles",
    "星币王后": "Queen of Pentacles",
    "星币皇后": "Queen of Pentacles",
    "星币国王": "King of Pentacles",
}

TAROT_HINTS = (
    "塔罗",
    "塔羅",
    "tarot",
    "牌义",
    "牌義",
    "解读",
    "解讀",
    "meaning",
    "reversed",
    "upright",
    "正位",
    "逆位",
    "韦特",
    "waite",
    "rider",
)


def english_card_name(card_zh: str, original: str = "") -> str:
    if card_zh in CARD_EN:
        return CARD_EN[card_zh]
    key = re.sub(r"\s+", " ", original.strip().lower())
    if key and not re.search(r"[\u4e00-\u9fff]", key):
        return original.strip().title()
    return card_zh


def plan_keywords(data: dict[str, str]) -> dict[str, object]:
    card_zh = normalize_card(data["card"])
    orientation = data["orientation"].strip() or "逆"
    orientation_full = "逆位" if "逆" in orientation else "正位"
    card_en = english_card_name(card_zh, data["card"])
    orientation_en = "reversed" if "逆" in orientation_full else "upright"
    raw = chat(
        [
            {
                "role": "system",
                "content": "只输出 JSON，不要 Markdown，不要解释。",
            },
            {
                "role": "user",
                "content": f"""根据塔罗牌信息输出 JSON：
牌名输入：{data['card']}
中文名参考：{card_zh}
英文名参考：{card_en}
正逆：{orientation}

格式：
{{
  "card_zh": "中文牌名（如权杖六）",
  "card_en": "English card name (e.g. Six of Wands)",
  "orientation": "正位或逆位",
  "keywords": ["中文关键词1", "中文关键词2", "English keyword 1", "English keyword 2"]
}}

关键词必须恰好 4 个：前 2 个中文、后 2 个英文，适合检索塔罗牌义。
例如：
["权杖六逆位含义", "六权杖 逆位 解读", "Six of Wands reversed meaning", "Six of Wands tarot reversed"]""",
            },
        ],
        temperature=0.1,
    )
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise RuntimeError(f"关键词规划失败：{raw}")
    plan = json.loads(match.group(0))
    keywords = [str(item).strip() for item in (plan.get("keywords") or []) if str(item).strip()]
    if len(keywords) < 4:
        keywords = [
            f"{card_zh}{orientation_full}含义",
            f"{card_zh} {orientation_full} 塔罗 解读",
            f"{card_en} {orientation_en} meaning",
            f"{card_en} tarot {orientation_en}",
        ]
    return {
        "card_zh": plan.get("card_zh") or card_zh,
        "card_en": plan.get("card_en") or card_en,
        "orientation": plan.get("orientation") or orientation_full,
        "keywords": keywords[:4],
    }


def build_web_queries(plan: dict[str, object]) -> list[str]:
    card_zh = str(plan["card_zh"])
    card_en = str(plan.get("card_en") or english_card_name(card_zh))
    orientation = str(plan["orientation"])
    orientation_en = "reversed" if "逆" in orientation else "upright"
    queries = list(plan.get("keywords") or [])
    queries.extend(
        [
            f"{card_zh} {orientation} 塔罗 牌义",
            f"{card_zh} {orientation} 正逆位 解析",
            f"{card_en} {orientation_en} tarot meaning",
            f"{card_en} rider waite {orientation_en}",
            f"site:labyrinthos.co {card_en}",
            f"site:biddytarot.com {card_en}",
            f"{card_zh} 塔罗 韦特",
        ]
    )
    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        key = re.sub(r"\s+", " ", query.strip().lower())
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(query.strip())
    return deduped


def is_tarot_result(title: str, snippet: str, url: str) -> bool:
    blob = f"{title} {snippet} {url}".lower()
    return any(hint.lower() in blob for hint in TAROT_HINTS)


def fetch_page_excerpt(ddgs: object, url: str, limit: int = 1800) -> str:
    try:
        page = ddgs.extract(url)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return ""
    if isinstance(page, dict):
        text = str(page.get("content") or page.get("text") or page.get("body") or "")
    else:
        text = str(page or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def search_references(
    keywords: list[str],
    per_keyword: int = 8,
    max_results: int = 18,
    extract_top: int = 8,
) -> list[dict[str, str]]:
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise RuntimeError(
            "虚拟环境中缺少 ddgs。请运行：./daily-one.sh\n"
            "或：.venv/bin/pip install ddgs"
        ) from exc

    refs: list[dict[str, str]] = []
    seen: set[str] = set()
    ddgs = DDGS()
    for keyword in keywords:
        print(f"搜索：{keyword}")
        try:
            results = ddgs.text(keyword, region="wt-wt", max_results=per_keyword) or []
        except Exception as exc:  # noqa: BLE001 - search backends vary
            print(f"  警告：搜索失败（{exc}），继续")
            results = []
        for item in results:
            href = (item.get("href") or "").strip()
            title = (item.get("title") or "").strip()
            snippet = (item.get("body") or "").strip()
            if not href or href in seen:
                continue
            if not is_tarot_result(title, snippet, href):
                continue
            seen.add(href)
            refs.append(
                {
                    "keyword": keyword,
                    "title": title,
                    "url": href,
                    "snippet": snippet,
                    "excerpt": "",
                }
            )
            if len(refs) >= max_results:
                break
        if len(refs) >= max_results:
            break

    print(f"抓取前 {min(extract_top, len(refs))} 篇网页正文摘录……")
    for item in refs[:extract_top]:
        excerpt = fetch_page_excerpt(ddgs, item["url"])
        if excerpt:
            item["excerpt"] = excerpt
            print(f"  ✓ {item['title'][:48]}")
        else:
            print(f"  · 仅摘要：{item['title'][:48]}")
    return refs


def format_refs(refs: list[dict[str, str]]) -> str:
    if not refs:
        return "（本次未能检索到外部资料，请仅基于经典塔罗牌义与本地博客做解析。）"
    lines = []
    for idx, item in enumerate(refs, 1):
        body = item.get("excerpt") or item.get("snippet") or ""
        lines.append(
            f"{idx}. [{item['keyword']}] {item['title']}\n"
            f"   URL: {item['url']}\n"
            f"   内容: {body}"
        )
    return "\n".join(lines)


def search_local_sources(
    terms: list[str],
    max_sources: int = 5,
    excerpt_radius: int = 1400,
) -> list[dict[str, str]]:
    """Find card-specific excerpts in the user's Tarot blog posts."""
    if not BLOG_POSTS.is_dir():
        return []

    clean_terms = [term.strip() for term in terms if term and term.strip()]
    matches: list[dict[str, object]] = []
    for path in BLOG_POSTS.glob("*.md"):
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        frontmatter = content[:1200].lower()
        if "tarot" not in frontmatter and "塔罗" not in frontmatter:
            continue

        title_match = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', content, re.M)
        title = title_match.group(1) if title_match else path.stem
        card_headings = list(re.finditer(r"^(#{3,4})\s+.*$", content, re.M))

        for term in clean_terms:
            term_lower = term.lower()
            # Only accept exact Tarot headings (major cards use ###, minor
            # cards use ####). Generic prose matches such as “世界” in a
            # relationship article are intentionally ignored.
            for index, heading in enumerate(card_headings):
                if term_lower in heading.group(0).lower():
                    level = len(heading.group(1))
                    section_end = min(len(content), heading.end() + excerpt_radius * 2)
                    for next_heading in card_headings[index + 1 :]:
                        if len(next_heading.group(1)) <= level:
                            section_end = next_heading.start()
                            break
                    matches.append(
                        {
                            "score": 1000,
                            "title": f"{title}｜{term}",
                            "path": str(path),
                            "excerpt": content[heading.start():section_end].strip(),
                        }
                    )
                    break

    matches.sort(key=lambda item: int(item["score"]), reverse=True)
    return [
        {
            "title": str(item["title"]),
            "path": str(item["path"]),
            "excerpt": str(item["excerpt"]),
        }
        for item in matches[:max_sources]
    ]


def format_local_sources(sources: list[dict[str, str]]) -> str:
    if not sources:
        return "（本地博客中没有找到相关内容。）"
    return "\n\n".join(
        f"### 本地资料 {index}：{source['title']}\n"
        f"文件：{source['path']}\n"
        f"摘录：\n{source['excerpt']}"
        for index, source in enumerate(sources, 1)
    )


def build_prompt(
    data: dict[str, str],
    plan: dict[str, object],
    refs: list[dict[str, str]],
    local_sources: list[dict[str, str]],
    verification: str = "",
) -> str:
    card_zh = str(plan["card_zh"])
    orientation = str(plan["orientation"])
    keywords = plan["keywords"]
    corpus_card = plan.get("corpus_card")
    corpus_block = (
        format_corpus_card(corpus_card, orientation)
        if isinstance(corpus_card, dict)
        else "（本地语料未命中该牌，请依赖博客摘录与网络资料。）"
    )
    web_block = format_refs(refs) if refs else "（未获取网络资料。）"
    verify_block = verification or "（未完成校验。）"
    return f"""你是塔罗标准解析写作者。请生成「独立单牌标准解析」，不结合个人过往。

日期：{data['date']}
牌名：{card_zh}
正逆：{orientation}
用户原始输入：{data['card']} / {data['orientation']}
今日问题：{data.get('question') or '无'}
补充记录：{data.get('notes') or '无'}

本地标准语料（第一优先级）：
{corpus_block}

本地博客摘录：
{format_local_sources(local_sources)}

网络塔罗资料（第二优先级，已校验）：
{web_block}

资料校验摘要（必须吸收；冲突处以本地语料+共识为准）：
{verify_block}

输出要求：
1. 只输出 Markdown，不要代码围栏。
2. 第一行必须是一行摘要，格式严格如下（不要加标题符号）：
{data['date']} 每日一抽{card_zh} {orientation}<5个核心关键词，顿号分隔><4条行动建议，顿号/逗号分隔>

3. 第一行之后空一行，再输出完整正文：

# {card_zh} {orientation}｜独立单牌标准解析（不结合个人过往）

## 核心总义
## 一、财运物质
## 二、事业学业
## 三、人际感情
## 四、情绪心态
## 五、通用行动指引
## 简短总结
## 参考资料

4. 优先采用「资料校验摘要」中的关键词与行动方向；网络补充可丰富表达，但不得与本地韦特牌义矛盾而不加说明。
5. 解析用于自我觉察，不断言命运，不提供医疗/法律/财务承诺。
6. 不要编造用户未提供的个人事件。
"""


def card_fingerprint(plan: dict[str, object]) -> str:
    return f"{plan['card_zh']}|{plan['orientation']}"


def with_card_meta(markdown: str, fingerprint: str) -> str:
    meta = f"<!-- tarot-cards: {fingerprint} -->\n"
    text = markdown.lstrip()
    if text.startswith("<!-- tarot-cards:"):
        text = re.sub(r"^<!-- tarot-cards:.*?-->\s*", "", text, count=1, flags=re.S)
    return meta + text.rstrip() + "\n"


def extract_card_meta(text: str) -> str | None:
    match = re.search(r"<!--\s*tarot-cards:\s*(.*?)\s*-->", text)
    if match:
        return match.group(1).strip()
    # Fallback for older daily files without meta comment.
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    # e.g. "2026-07-19 每日一抽圣杯七 正位|..."
    m = re.search(r"每日一抽\s*([^\s|]+)\s*(正位|逆位|正|逆)", first)
    if m:
        orient = "逆位" if "逆" in m.group(2) else "正位"
        return f"{m.group(1)}|{orient}"
    return None


def save(day: str, markdown: str, fingerprint: str, *, yes: bool = False) -> Path:
    """Save daily note. Different cards → new file; same cards → ask to overwrite."""
    year, month, _ = day.split("-")
    directory = ROOT / year / month
    directory.mkdir(parents=True, exist_ok=True)
    primary = directory / f"{day}.md"
    body = with_card_meta(markdown, fingerprint)

    if not primary.exists():
        primary.write_text(body, encoding="utf-8")
        return primary

    existing = extract_card_meta(primary.read_text(encoding="utf-8"))
    if existing == fingerprint:
        if not yes:
            answer = input(
                f"{primary} 已有相同牌面（{fingerprint}），覆盖？[y/N]: "
            ).strip().lower()
            if answer != "y":
                raise RuntimeError("已取消，原文件未修改")
        primary.write_text(body, encoding="utf-8")
        print(f"已覆盖同牌面文件：{primary}")
        return primary

    from datetime import datetime as dt

    destination = directory / f"{day}-{dt.now().strftime('%H%M%S')}.md"
    destination.write_text(body, encoding="utf-8")
    old_label = existing or "未知牌面"
    print(
        f"牌面不同（已有：{old_label} → 本次：{fingerprint}），"
        f"保留 {primary.name}，另存为 {destination.name}"
    )
    return destination


def parse_args(argv: list[str]) -> dict[str, object]:
    offline = "--offline" in argv
    draw = "--draw" in argv or "--auto" in argv
    yes = "--yes" in argv or "-y" in argv
    question: str | None = None
    seed: str | None = None
    day_args: list[str] = []
    args = argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--question", "-q") and i + 1 < len(args):
            question = args[i + 1]
            i += 2
            continue
        if arg.startswith("--question="):
            question = arg.split("=", 1)[1]
            i += 1
            continue
        if arg == "--seed" and i + 1 < len(args):
            seed = args[i + 1]
            i += 2
            continue
        if arg.startswith("--") or arg in ("-y",):
            i += 1
            continue
        day_args.append(arg)
        i += 1
    day = day_args[0] if day_args else date.today().isoformat()
    return {
        "day": day,
        "offline": offline,
        "draw": draw,
        "yes": yes,
        "question": question,
        "seed": seed,
    }


def confirm_plan(plan: dict[str, object], *, yes: bool = False) -> None:
    print("\n确认牌面：")
    print(f"  {plan['card_zh']} / {plan.get('card_en', '')} {plan['orientation']}")
    print(f"  本地语料：{'命中' if plan.get('corpus_card') else '未命中'}")
    if yes:
        return
    answer = input("开始生成？[Y/n]: ").strip().lower()
    if answer in ("n", "no"):
        raise RuntimeError("已取消")


def main() -> int:
    opts = parse_args(sys.argv)
    day = str(opts["day"])
    offline = bool(opts["offline"])
    ensure_venv_python(need_web=not offline)
    try:
        from research import gather_for_single

        date.fromisoformat(day)
        data = collect(
            day,
            draw=bool(opts["draw"]),
            question=opts["question"] if isinstance(opts["question"], str) else None,
            seed=opts["seed"] if isinstance(opts["seed"], str) else None,
        )

        print("\n1/4 本地语料 + 博客……")
        plan = resolve_card_plan(data)
        confirm_plan(plan, yes=bool(opts["yes"]))

        print("\n2/4 网络搜索（带本地 cache）……")
        if offline:
            print("  --offline：跳过联网")
        research = gather_for_single(plan, data["card"], offline=offline)
        print(f"  博客摘录：{len(research['local_sources'])} 篇")
        print(f"  网络资料：{len(research['web_refs'])} 篇（{research['web_from']}）")

        print("\n3/4 API 校验（综合本地 + 网络）……")
        print("-" * 40)
        print(research["verification"])
        print("-" * 40)

        print("\n4/4 生成正式 Markdown……")
        markdown = chat(
            [
                {"role": "system", "content": "严格按用户要求输出 Markdown，第一行必须是摘要行。"},
                {
                    "role": "user",
                    "content": build_prompt(
                        data,
                        plan,
                        research["web_refs"],
                        research["local_sources"],
                        research["verification"],
                    ),
                },
            ],
            temperature=0.4,
        )
        destination = save(day, markdown, card_fingerprint(plan), yes=bool(opts["yes"]))
        print("\n" + "=" * 72)
        print(markdown)
        print("=" * 72)
        print(f"\n已保存：{destination}")
        return 0
    except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"\n错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
