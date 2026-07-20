#!/usr/bin/env python3
"""Gather, cache, and verify Tarot sources: local corpus → web → LLM check."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tarot_agent import (
    build_web_queries,
    chat,
    format_corpus_card,
    format_local_sources,
    format_refs,
    search_local_sources,
    search_references,
)

ROOT = Path(__file__).resolve().parent
WEB_CACHE_DIR = ROOT / "corpus" / "cache" / "web"
CACHE_TTL_DAYS = 30


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def cache_key(card_zh: str, card_en: str, orientation: str) -> str:
    orient = "reversed" if "逆" in orientation else "upright"
    return f"{_slug(card_en or card_zh)}_{orient}"


def cache_path(key: str) -> Path:
    return WEB_CACHE_DIR / f"{key}.json"


def load_web_cache(key: str) -> list[dict[str, str]] | None:
    path = cache_path(key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        fetched = datetime.fromisoformat(payload["fetched_at"])
        if datetime.now(timezone.utc) - fetched > timedelta(days=CACHE_TTL_DAYS):
            return None
        return payload.get("refs") or []
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None


def save_web_cache(
    key: str,
    plan: dict[str, object],
    queries: list[str],
    refs: list[dict[str, str]],
) -> None:
    WEB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "key": key,
        "card_zh": plan.get("card_zh"),
        "card_en": plan.get("card_en"),
        "orientation": plan.get("orientation"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "queries": queries,
        "refs": refs,
    }
    cache_path(key).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def fetch_web_sources(
    plan: dict[str, object],
    *,
    offline: bool = False,
    use_cache: bool = True,
    per_keyword: int = 6,
    max_results: int = 14,
    extract_top: int = 6,
) -> tuple[list[dict[str, str]], str]:
    """Return (refs, source_label). source_label is 'cache'|'network'|'skipped'."""
    if offline:
        return [], "skipped"

    key = cache_key(
        str(plan.get("card_zh") or ""),
        str(plan.get("card_en") or ""),
        str(plan.get("orientation") or ""),
    )
    if use_cache:
        cached = load_web_cache(key)
        if cached is not None:
            print(f"Web cache hit: {key}（{len(cached)} 篇）")
            return cached, "cache"

    queries = build_web_queries(plan)
    print(f"Web search ({len(queries)} queries)…")
    refs = search_references(
        queries,
        per_keyword=per_keyword,
        max_results=max_results,
        extract_top=extract_top,
    )
    if refs and use_cache:
        save_web_cache(key, plan, queries, refs)
        print(f"Wrote web cache: corpus/cache/web/{key}.json")
    return refs, "network"


def verify_sources(
    plan: dict[str, object],
    corpus_card: dict[str, object] | None,
    local_sources: list[dict[str, str]],
    web_refs: list[dict[str, str]],
) -> str:
    """One LLM call: compare local vs web, return verification notes for final prompt."""
    orientation = str(plan.get("orientation") or "")
    corpus_block = (
        format_corpus_card(corpus_card, orientation)
        if isinstance(corpus_card, dict)
        else "（本地语料未命中）"
    )
    web_block = format_refs(web_refs) if web_refs else "（无网络资料）"
    blog_block = format_local_sources(local_sources)

    return chat(
        [
            {
                "role": "system",
                "content": (
                    "你是塔罗资料校验员。只输出 Markdown 小节，不用代码围栏。"
                    "不编造资料，只基于给定文本比较。"
                ),
            },
            {
                "role": "user",
                "content": f"""比较以下来源，输出校验摘要（供后续写正式解析使用）：

牌：{plan.get('card_zh')} / {plan.get('card_en')} {orientation}

## 本地标准语料
{corpus_block}

## 本地博客摘录
{blog_block}

## 网络资料
{web_block}

请输出以下结构（简体中文）：

## 一致共识
（本地与网络共同支持的核心牌义，3～6 条）

## 网络补充
（网络有、本地语料较简略或未强调的现代解读角度，2～5 条；无则写“无显著补充”）

## 差异或冲突
（如有不同侧重点或矛盾，逐条说明；无则写“未发现重大冲突”）

## 建议关键词
（5 个核心关键词，顿号分隔）

## 建议行动方向
（4 条温和可执行建议，顿号或逗号分隔）

要求：不断言命运；不添加资料中未出现的具体事件。""",
            },
        ],
        temperature=0.2,
    )


def gather_for_single(
    plan: dict[str, object],
    raw_card: str,
    *,
    offline: bool = False,
) -> dict[str, object]:
    """Full research pipeline for one card."""
    local_sources = search_local_sources(
        [
            str(plan.get("card_zh") or ""),
            str(plan.get("card_en") or ""),
            raw_card,
        ]
    )
    web_refs, web_from = fetch_web_sources(plan, offline=offline)
    verification = verify_sources(
        plan,
        plan.get("corpus_card") if isinstance(plan.get("corpus_card"), dict) else None,
        local_sources,
        web_refs,
    )
    return {
        "local_sources": local_sources,
        "web_refs": web_refs,
        "web_from": web_from,
        "verification": verification,
    }


def verify_spread(
    cards: list[dict[str, object]],
    corpus_blocks: str,
    local_sources: list[dict[str, str]],
    web_refs: list[dict[str, str]],
) -> str:
    """One LLM call for a multi-card spread; keep each card distinct."""
    locked = "\n".join(
        f"{index}. 【{item['position']}】{item['card_zh']} / {item['card_en']} {item['orientation']}"
        for index, item in enumerate(cards, 1)
    )
    web_block = format_refs(web_refs) if web_refs else "（无网络资料）"
    blog_block = format_local_sources(local_sources)
    corpus_text = corpus_blocks or "（本地语料未命中）"

    return chat(
        [
            {
                "role": "system",
                "content": (
                    "你是塔罗牌阵资料校验员。只输出 Markdown 小节，不用代码围栏。"
                    "严禁改写、合并或替换牌名与位置；逐牌对照给定文本。"
                ),
            },
            {
                "role": "user",
                "content": f"""以下牌阵已锁定，校验时必须按此顺序逐牌处理，不得换成其他牌：

{locked}

## 本地标准语料（按位置）
{corpus_text}

## 本地博客摘录
{blog_block}

## 网络资料（可能混有多张牌，请按牌名归属）
{web_block}

请输出（简体中文）：

## 锁定牌阵确认
（原样复述上面的 N 行：位置｜牌名｜正逆）

## 逐牌共识
（为每张牌各写 2～4 条：位置｜牌名｜核心牌义；只写该牌）

## 网络补充
（按牌归类；无则写“无显著补充”）

## 差异或冲突
（无则写“未发现重大冲突”）

## 建议关键词表
（Markdown 表格：位置｜牌名｜正逆｜3～5 个关键词）

## 综合行动方向
（4 条温和可执行建议）

要求：不得出现锁定列表以外的牌名或“上位/中位/下位/杂牌”等位置名。""",
            },
        ],
        temperature=0.2,
    )


def gather_for_spread(
    cards: list[dict[str, object]],
    *,
    offline: bool = False,
) -> dict[str, object]:
    """Research each card in a spread; one combined verification pass."""
    all_local: list[dict[str, str]] = []
    all_web: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    corpus_blocks: list[str] = []

    for item in cards:
        mini_plan = {
            "card_zh": item["card_zh"],
            "card_en": item["card_en"],
            "orientation": item["orientation"],
            "keywords": [
                f"{item['card_zh']}{item['orientation']}含义",
                f"{item['card_en']} tarot meaning",
            ],
            "corpus_card": item.get("corpus_card"),
        }
        local = search_local_sources([item["card_zh"], item["card_en"]])
        for src in local:
            if src["path"] not in {x.get("path") for x in all_local}:
                all_local.append(src)

        web, _ = fetch_web_sources(mini_plan, offline=offline, max_results=8, extract_top=4)
        for ref in web:
            if ref["url"] not in seen_urls:
                seen_urls.add(ref["url"])
                # Tag which card this ref belongs to, so later prompts don't mix cards.
                tagged = dict(ref)
                tagged["title"] = f"[{item['position']}|{item['card_zh']}] {ref.get('title', '')}"
                all_web.append(tagged)

        if item.get("corpus_card"):
            corpus_blocks.append(
                f"### {item['position']}｜{item['card_zh']} {item['orientation']}\n"
                + format_corpus_card(item["corpus_card"], item["orientation"])
            )

    corpus_text = "\n\n".join(corpus_blocks)
    # Skip combined LLM verify for spreads: mixed sources often cause card bleed.
    # Per-card generation in question_agent handles meaning with isolation + fallback.
    return {
        "local_sources": all_local,
        "web_refs": all_web,
        "web_from": "skipped" if offline else "mixed",
        "verification": "",
        "corpus_blocks": corpus_text,
    }
