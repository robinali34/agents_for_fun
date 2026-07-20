#!/usr/bin/env python3
"""Question spreads (3/5 cards): local corpus → web+cache → generate."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

from tarot_agent import (
    ask,
    chat,
    ensure_venv_python,
    format_corpus_card,
    format_local_sources,
    format_refs,
    lookup_corpus_card,
)

ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("TAROT_DATA_ROOT", str(ROOT))).expanduser().resolve()

POSITIONS = {
    3: ["Situation", "Obstacle", "Advice"],
    5: ["Core", "Past influence", "Current state", "Challenge", "Action advice"],
}


def collect(
    day: str,
    count: int,
    *,
    draw: bool = False,
    question: str | None = None,
    seed: str | None = None,
) -> dict[str, object]:
    print(f"\nQuestion reading — {count} cards\n")
    q = question if question is not None else ask("Your question")
    if not q:
        raise RuntimeError("A question is required for 3/5-card readings")

    if draw:
        from deck import draw_cards, format_drawn

        positions = POSITIONS[count]
        drawn = draw_cards(count, seed=seed)
        print("\nAuto-draw:")
        print(format_drawn(drawn, positions))
        cards = [
            {
                "position": positions[index],
                "card": item["card_zh"],
                "orientation": item["orientation"],
            }
            for index, item in enumerate(drawn)
        ]
        context = "" if question is not None else ask("\nContext (optional)")
        return {"date": day, "question": q, "cards": cards, "context": context}

    cards: list[dict[str, str]] = []
    for index, position in enumerate(POSITIONS[count], 1):
        print(f"\nCard {index}｜{position}")
        cards.append(
            {
                "position": position,
                "card": ask("Card name"),
                "orientation": ask("Upright/Reversed (正/逆)"),
            }
        )
        if not cards[-1]["card"] or not cards[-1]["orientation"]:
            raise RuntimeError("每张牌的Card name和Upright/Reversed (正/逆)都必须填写")
    return {
        "date": day,
        "question": q,
        "cards": cards,
        "context": "" if question is not None else ask("\nContext (optional)"),
    }


def resolve_reading(data: dict[str, object]) -> dict[str, object]:
    from deck import fuzzy_lookup, suggest_cards

    resolved = []
    for item in data["cards"]:
        corpus = fuzzy_lookup(str(item["card"])) or lookup_corpus_card(str(item["card"]))
        orientation = str(item["orientation"]).strip()
        orientation_full = "逆位" if "逆" in orientation else "正位"
        if not corpus:
            tips = suggest_cards(str(item["card"]))
            tip_text = "; suggestions: " + "、".join(tips) if tips else ""
            raise RuntimeError(
                f"未识别Card name「{item['card']}' (position: {item['position']}）{tip_text}"
            )
        card_zh = str(corpus.get("name_zh"))
        card_en = str(corpus.get("name_en"))
        resolved.append(
            {
                "position": item["position"],
                "card_zh": card_zh,
                "card_en": card_en,
                "orientation": orientation_full,
                "corpus_card": corpus,
            }
        )
    names_zh = " ".join(item["card_zh"] for item in resolved)
    names_en = " ".join(item["card_en"] for item in resolved)
    return {
        "cards": resolved,
        "keywords": [
            f"{names_zh} 塔罗牌阵解读",
            f"{data['question']} 塔罗 建议",
            f"{names_en} tarot spread meaning",
            f"{data['question']} tarot advice",
        ],
    }


def locked_spread_lines(plan: dict[str, object]) -> str:
    return "\n".join(
        f"{index}. 【{item['position']}】{item['card_zh']} / {item['card_en']} {item['orientation']}"
        for index, item in enumerate(plan["cards"], 1)
    )


def extract_json_object(raw: str) -> dict[str, object]:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise RuntimeError("Model did not return usable JSON")
    return json.loads(match.group(0))


def refs_for_card(
    refs: list[dict[str, str]],
    item: dict[str, object],
) -> list[dict[str, str]]:
    tag = f"[{item['position']}|{item['card_zh']}]"
    tagged = [ref for ref in refs if tag in str(ref.get("title") or "")]
    if tagged:
        return tagged
    name_zh = str(item["card_zh"])
    name_en = str(item.get("card_en") or "")
    return [
        ref
        for ref in refs
        if name_zh in str(ref.get("title") or "")
        or name_zh in str(ref.get("snippet") or "")
        or (name_en and name_en.lower() in str(ref.get("title") or "").lower())
    ]


def corpus_keywords_fallback(item: dict[str, object]) -> str:
    card = item.get("corpus_card")
    if not isinstance(card, dict):
        return f"{item['card_zh']}、{item['orientation']}、{item['position']}"
    orientation = str(item["orientation"])
    raw = str(
        card.get("reversed_zh") if "逆" in orientation else card.get("upright_zh") or ""
    )
    raw = re.sub(r"\s+", " ", raw).strip()
    # Prefer short clauses separated by common Chinese punctuation.
    parts = [p.strip(" ：:。；;") for p in re.split(r"[。；;\n]", raw) if p.strip()]
    picked: list[str] = []
    for part in parts:
        if 2 <= len(part) <= 18:
            picked.append(part)
        if len(picked) >= 4:
            break
    if not picked and raw:
        picked = [raw[:24]]
    return "、".join(picked[:4]) if picked else str(item["card_zh"])


def corpus_reading_fallback(item: dict[str, object]) -> str:
    card = item.get("corpus_card")
    pos = item["position"]
    card_zh = item["card_zh"]
    orientation = item["orientation"]
    if not isinstance(card, dict):
        return (
            f"在「{pos}」位置，{card_zh}{orientation}提示关注该牌位主题；"
            f"请结合问题做温和复盘，勿过度断言。"
        )
    body = format_corpus_card(card, str(orientation)).strip()
    if len(body) > 900:
        body = body[:900].rstrip() + "…"
    return f"在「{pos}」位置，围绕 {card_zh}{orientation}：\n{body}"


def mentions_other_cards(text: str, item: dict[str, object], cards: list[dict[str, object]]) -> bool:
    for other in cards:
        other_zh = str(other["card_zh"])
        if other_zh == item["card_zh"]:
            continue
        if other_zh and other_zh in text:
            return True
    return False


ROMANCE_BAN = (
    "爱情",
    "恋爱",
    "情侣",
    "伴侣",
    "暧昧",
    "表白",
    "两性",
    "桃花",
    "对方心里",
    "他心里",
    "她心里",
    "恋人",
    "男友",
    "女友",
    "夫妻",
    "婚姻",
    "约会",
    "共度时光",
    "两人共度",
    "情感关系",
    "关系质量",
    "增进关系",
)


def question_is_non_romance(question: str, context: str = "") -> bool:
    text = f"{question} {context}"
    love_q = any(
        k in text
        for k in ("爱情", "恋爱", "感情", "对象", "相亲", "分手", "复合", "婚姻", "伴侣")
    )
    return not love_q


def contains_romance(text: str) -> bool:
    return any(k in text for k in ROMANCE_BAN)


def question_focus(question: str, context: str = "") -> str:
    """Short domain hint so Cups/etc. are mapped to the asked topic, not default romance."""
    text = f"{question} {context}"
    love = ("爱情", "恋爱", "感情", "对象", "相亲", "分手", "复合", "婚姻", "伴侣")
    if any(k in text for k in love):
        return "本题偏感情关系；可用情感类牌义，但仍要具体回答该问题。"
    work = ("工作", "事业", "职场", "面试", "升职", "项目", "同事", "老板")
    if any(k in text for k in work):
        return "本题偏工作/事业；把牌义映射到任务、协作、节奏、优先级。禁止出现伴侣/恋爱等词。"
    schedule = ("安排", "计划", "日程", "下周", "这周", "时间", "行程", "怎么过", "如何安排")
    if any(k in text for k in schedule):
        return (
            "本题偏「时间/事务安排」。只能谈：优先级、日程块、协作对齐、情绪负荷、取舍、留白。"
            "禁止出现：伴侣、恋爱、情侣、两人共度、情感关系、桃花等任何恋爱用语。"
        )
    study = ("学习", "考试", "学业", "论文", "复习")
    if any(k in text for k in study):
        return "本题偏学习；映射到专注、节奏、资源与心态。禁止恋爱用语。"
    return (
        "紧扣用户原问题作答；经典牌义只作隐喻。"
        "若用户未问感情，禁止出现伴侣/恋爱等词。"
    )


def reading_off_topic(question: str, context: str, reading: str, keywords: str) -> bool:
    """For non-romance questions, any romance wording is off-topic."""
    if not question_is_non_romance(question, context):
        return False
    return contains_romance(f"{reading} {keywords}")


def practical_card_fallback(
    data: dict[str, object],
    item: dict[str, object],
) -> dict[str, str]:
    """Deterministic, question-locked text when the model keeps drifting to romance."""
    pos = str(item["position"])
    card = str(item["card_zh"])
    orient = str(item["orientation"])
    q = str(data["question"])
    key = (card, orient)
    presets = {
        ("圣杯二", "正位"): (
            "协作对齐、互信、共同目标、沟通成本",
            f"针对「{q}」，在「{pos}」：{card}{orient}提示先与关键协作方对齐目标和可用时间窗口，"
            f"用清晰约定降低反复沟通，把「和谐」落成可执行的共同日程，而不是偏离「{q}」。",
        ),
        ("圣杯二", "逆位"): (
            "错位、沟通不畅、目标不一致、反复返工",
            f"针对「{q}」，在「{pos}」：{card}{orient}提示协作节奏不合或目标没对齐，"
            f"先暂停加塞新事项，把分歧写成可勾选的对齐清单再排下周。",
        ),
        ("圣杯骑士", "正位"): (
            "愿景、热情、邀请、推动",
            f"针对「{q}」，在「{pos}」：{card}{orient}提示可用热情推动一件真正想推进的事，"
            f"但要把热情落成具体时段与交付，而不是停留在想法。",
        ),
        ("圣杯骑士", "逆位"): (
            "空想、情绪波动、动力不稳、承诺过热",
            f"针对「{q}」，在「{pos}」：{card}{orient}提示情绪化承诺或不切实际的计划会打乱日程；"
            f"先砍掉高热情低可行性事项，再排可完成的周计划。",
        ),
        ("死神", "正位"): (
            "结束旧项、腾挪空间、结构重排",
            f"针对「{q}」，在「{pos}」：{card}{orient}提示主动结束过期任务/习惯，"
            f"把腾出的时间块重分配给下周真正重要的事。",
        ),
        ("死神", "逆位"): (
            "拖延收尾、旧节奏未断、需要主动改",
            f"针对「{q}」，在「{pos}」：{card}{orient}提示不要拖着旧安排不放；"
            f"本周主动做一次收尾/删减，才能给下周腾出结构空间。",
        ),
    }
    if key in presets:
        keywords, reading = presets[key]
        return {"keywords": keywords, "reading": reading}
    return {
        "keywords": f"{pos}、优先级、节奏、取舍、留白",
        "reading": (
            f"针对「{q}」，在「{pos}」看 {card}{orient}："
            f"把牌义译成时间安排与精力管理——先定必须完成项，再删减干扰，最后留弹性空白。"
        ),
    }


def generate_one_card(
    data: dict[str, object],
    item: dict[str, object],
    all_cards: list[dict[str, object]],
    refs: list[dict[str, str]],
) -> dict[str, str]:
    """One focused LLM call for a single locked card."""
    corpus = (
        format_corpus_card(item["corpus_card"], str(item["orientation"]))
        if isinstance(item.get("corpus_card"), dict)
        else "（本地语料未命中）"
    )
    non_romance = question_is_non_romance(
        str(data["question"]), str(data.get("context") or "")
    )
    # Romance-heavy web pages pull Cups readings toward dating; skip them off-topic.
    if non_romance:
        card_refs: list[dict[str, str]] = []
        web_block = "（本题非感情问题，已跳过易跑题的网络摘录；仅用本地语料做语境映射。）"
    else:
        card_refs = refs_for_card(refs, item)
        web_block = format_refs(card_refs) if card_refs else "（无专属网络资料，仅用本地语料）"
    other_names = "、".join(
        str(c["card_zh"]) for c in all_cards if c["card_zh"] != item["card_zh"]
    )
    focus = question_focus(str(data["question"]), str(data.get("context") or ""))
    ban = "、".join(ROMANCE_BAN[:12])
    prompt = f"""只解读这一张牌。输出 JSON，不要 Markdown。

【用户问题】{data['question']}
【背景】{data.get('context') or '无'}
【答题焦点】{focus}

位置：{item['position']}
本牌：{item['card_zh']} / {item['card_en']} {item['orientation']}

本地语料（经典牌义，必须翻译到用户问题语境）：
{corpus}

补充资料：
{web_block}

输出：
{{
  "keywords": "3～5 个关键词，顿号分隔；必须服务用户问题",
  "reading": "2～4 句：直接回答用户问题在本位置的含义与可执行安排"
}}

硬性规则：
1. 每一句都要能回答「{data['question']}」。
2. 只能写 {item['card_zh']}，禁止其他Card name（{other_names or '无'}）。
3. {"禁止出现这些词：" + ban + "。把「爱/和谐」改写成协作、对齐、信任、情绪负荷。" if non_romance else "可谈感情，但仍要具体回答原问题。"}
4. 不断言命运；不提供医疗/法律/投资承诺。
"""
    raw = chat(
        [
            {
                "role": "system",
                "content": (
                    f"Output JSON only. Write values in English. 解读【{item['position']}】的{item['card_zh']}{item['orientation']}。"
                    f"必须紧扣「{data['question']}」。"
                    + ("严禁伴侣/恋爱等词。" if non_romance else "")
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    try:
        payload = extract_json_object(raw)
    except (RuntimeError, json.JSONDecodeError):
        payload = {}

    keywords = str(payload.get("keywords") or "").strip()
    reading = str(payload.get("reading") or "").strip()
    bad = (
        not reading
        or mentions_other_cards(reading, item, all_cards)
        or mentions_other_cards(keywords, item, all_cards)
        or reading_off_topic(
            str(data["question"]), str(data.get("context") or ""), reading, keywords
        )
    )
    if bad:
        retry = chat(
            [
                {
                    "role": "system",
                    "content": (
                        "Output JSON only. Write values in English. 上一次不合格（跑题或串牌）。"
                        f"必须直接回答「{data['question']}」，只写 {item['card_zh']}{item['orientation']}。"
                        + (f"禁止词：{ban}" if non_romance else "")
                    ),
                },
                {
                    "role": "user",
                    "content": f"""输出 JSON：
{{
  "keywords": "3～5 个与问题相关的词",
  "reading": "2～4 句可执行安排，零恋爱用语"
}}

问题：{data['question']}
焦点：{focus}
位置：{item['position']}
牌：{item['card_zh']}{item['orientation']}
语料摘要（勿照抄恋爱句）：{corpus_keywords_fallback(item)}
""",
                },
            ],
            temperature=0.1,
        )
        try:
            payload = extract_json_object(retry)
            keywords = str(payload.get("keywords") or "").strip()
            reading = str(payload.get("reading") or "").strip()
        except (RuntimeError, json.JSONDecodeError):
            keywords, reading = "", ""

    if (
        not reading
        or mentions_other_cards(reading, item, all_cards)
        or reading_off_topic(
            str(data["question"]), str(data.get("context") or ""), reading, keywords
        )
    ):
        return practical_card_fallback(data, item)
    return {"keywords": keywords, "reading": reading}


def generate_synthesis(
    data: dict[str, object],
    plan: dict[str, object],
    per_card: dict[str, dict[str, str]],
) -> dict[str, object]:
    """Final call: connect already-written card readings; do not restate wrong cards."""
    locked = locked_spread_lines(plan)
    focus = question_focus(str(data["question"]), str(data.get("context") or ""))
    non_romance = question_is_non_romance(
        str(data["question"]), str(data.get("context") or "")
    )
    q = str(data["question"])
    card_blocks = []
    for item in plan["cards"]:
        pos = str(item["position"])
        piece = per_card[pos]
        card_blocks.append(
            f"### {pos}｜{item['card_zh']} {item['orientation']}\n"
            f"关键词：{piece['keywords']}\n"
            f"{piece['reading']}"
        )
    ban = "、".join(ROMANCE_BAN[:12])
    prompt = f"""基于「已写好的逐牌解读」做综合，输出 JSON（不要 Markdown）。

【用户问题】{q}
【背景】{data.get('context') or '无'}
【答题焦点】{focus}

锁定牌阵：
{locked}

已写好的逐牌解读：
{chr(10).join(card_blocks)}

输出：
{{
  "conclusion": "一句话，必须直接回答用户问题",
  "actions_summary": "一句话可执行安排摘要",
  "background": "问题与背景改写，2～4 句",
  "connections": "三张如何共同回答该问题",
  "answer": "综合回答：具体到时间/事务/精力怎么排",
  "advice": ["安排1", "安排2", "安排3", "安排4"],
  "reflection": "紧扣原问题的反思",
  "risks": "风险与边界，2～3 句"
}}

硬性规则：
1. conclusion / answer / advice 必须像在回答「{q}」。
2. {"禁止出现：" + ban if non_romance else "可谈感情但仍要答原问题。"}
3. 不要引入新Card name。
"""
    raw = chat(
        [
            {
                "role": "system",
                "content": (
                    f"Output JSON only. Write values in English. 直接回答「{q}」。"
                    + ("严禁伴侣/恋爱等词。" if non_romance else "")
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    try:
        payload = extract_json_object(raw)
    except (RuntimeError, json.JSONDecodeError):
        payload = {}

    blob = " ".join(
        str(payload.get(k) or "")
        for k in ("conclusion", "actions_summary", "background", "connections", "answer", "reflection")
    )
    advice = payload.get("advice") if isinstance(payload.get("advice"), list) else []
    blob += " " + " ".join(str(x) for x in advice)

    if (not payload.get("answer")) or (
        non_romance and contains_romance(blob)
    ):
        return {
            "conclusion": f"围绕「{q}」先定优先级，再按现状—阻碍—建议推进",
            "actions_summary": "列出必须做 / 可推迟 / 需协作，并留弹性空白",
            "background": str(data.get("context") or q),
            "connections": "\n\n".join(card_blocks),
            "answer": (
                f"针对「{q}」：用「现状」盘点可用时间与协作资源；"
                f"用「阻碍」标出最耗精力的干扰并压缩它；"
                f"用「建议」主动结束旧节奏、重排下周日程。"
            ),
            "advice": [
                "写出下周必须完成的 3 件事并标定截止",
                "标出最耗精力的干扰项，限时处理或删除",
                "为必要协作预留固定沟通时段",
                "留出半天空白以防变动",
            ],
            "reflection": f"若只为「{q}」服务，你最先该砍掉的是什么？",
            "risks": "塔罗用于自我觉察，不替代专业建议。",
        }
    return payload


def assemble_markdown(
    data: dict[str, object],
    plan: dict[str, object],
    payload: dict[str, object],
    refs: list[dict[str, str]],
    local_sources: list[dict[str, str]],
) -> str:
    """Build final markdown in code so the spread table/order cannot drift."""
    count = len(plan["cards"])
    non_romance = question_is_non_romance(
        str(data["question"]), str(data.get("context") or "")
    )
    conclusion = str(payload.get("conclusion") or "see body")
    actions_summary = str(payload.get("actions_summary") or "see body建议")
    background = str(payload.get("background") or data.get("context") or data["question"])
    keywords = payload.get("keywords") if isinstance(payload.get("keywords"), dict) else {}
    per_card = payload.get("per_card") if isinstance(payload.get("per_card"), dict) else {}
    advice = payload.get("advice") if isinstance(payload.get("advice"), list) else []
    if not advice:
        advice = ["结合牌义复盘本周重点", "先处理可控事项", "保留弹性时间", "避免过度承诺"]

    overview_rows = [
        "| 位置 | Card name | 正逆位 | 关键词 |",
        "|------|------|--------|--------|",
    ]
    card_sections: list[str] = []
    for item in plan["cards"]:
        pos = str(item["position"])
        card_zh = str(item["card_zh"])
        orientation = str(item["orientation"])
        kw = str(keywords.get(pos) or "see body")
        body = str(per_card.get(pos) or "").strip()
        if (not body) or (non_romance and contains_romance(f"{kw} {body}")):
            fb = practical_card_fallback(data, item)
            kw = fb["keywords"]
            body = fb["reading"]
        overview_rows.append(f"| {pos} | {card_zh} | {orientation} | {kw} |")
        card_sections.append(f"### {pos}：{card_zh}（{orientation}）\n{body}")

    advice_lines = "\n".join(f"{idx}. {str(item).strip()}" for idx, item in enumerate(advice, 1))
    ref_lines: list[str] = []
    for src in local_sources[:8]:
        ref_lines.append(f"- 本地：{src.get('title') or src.get('path')}（{src.get('path')}）")
    if not non_romance:
        for ref in refs[:10]:
            ref_lines.append(f"- {ref.get('title') or '资料'} — {ref.get('url')}")
    else:
        ref_lines.append("- Local corpus corpus/waite-rws.json(non-romance question; romance-heavy web excerpts omitted)")
    if not ref_lines:
        ref_lines.append("- Local corpus corpus/waite-rws.json")

    answer = str(payload.get("answer") or conclusion)
    connections = str(payload.get("connections") or "（见综合回答）")
    reflection = str(payload.get("reflection") or "这三张牌分别提醒你关注什么？")
    if non_romance and contains_romance(
        f"{conclusion} {actions_summary} {background} {connections} {answer} {advice_lines} {reflection}"
    ):
        # Hard override synthesis fields that still leaked romance.
        conclusion = f"围绕「{data['question']}」先定优先级，再按现状—阻碍—建议推进"
        actions_summary = "列出必须做 / 可推迟 / 需协作，并留弹性空白"
        background = str(data.get("context") or data["question"])
        connections = "三张牌分别对应：可用资源与协作、最耗精力的干扰、需要主动收尾并重排的旧节奏。"
        answer = (
            f"针对「{data['question']}」：先盘点可用时间与协作资源，"
            f"压缩最耗精力的干扰，再主动结束旧安排、重排下周日程。"
        )
        advice_lines = "\n".join(
            f"{idx}. {line}"
            for idx, line in enumerate(
                [
                    "写出下周必须完成的 3 件事并标定截止",
                    "标出最耗精力的干扰项，限时处理或删除",
                    "为必要协作预留固定沟通时段",
                    "留出半天空白以防变动",
                ],
                1,
            )
        )
        reflection = f"若只为「{data['question']}」服务，你最先该砍掉的是什么？"

    parts = [
        f"{data['date']} {count}-card reading｜{data['question']}｜{conclusion}｜{actions_summary}",
        "",
        f"# {count}-card reading｜{data['question']}",
        "",
        "## Question & context",
        background,
        "",
        "## Spread overview",
        "\n".join(overview_rows),
        "",
        "## Card-by-card",
        "\n\n".join(card_sections),
        "",
        "## How the cards connect",
        connections,
        "",
        "## Answer to the question",
        answer,
        "",
        "## Actionable advice",
        advice_lines,
        "",
        "## Reflection",
        reflection,
        "",
        "## Risks & boundaries",
        str(payload.get("risks") or "塔罗用于自我觉察，不替代专业建议。"),
        "",
        "## References",
        "\n".join(ref_lines),
        "",
    ]
    return "\n".join(parts)


def spread_fingerprint(plan: dict[str, object]) -> str:
    parts = [
        f"{item['position']}:{item['card_zh']}|{item['orientation']}"
        for item in plan["cards"]
    ]
    return ";".join(parts)


def with_card_meta(markdown: str, fingerprint: str) -> str:
    meta = f"<!-- tarot-cards: {fingerprint} -->\n"
    text = markdown.lstrip()
    if text.startswith("<!-- tarot-cards:"):
        text = re.sub(r"^<!-- tarot-cards:.*?-->\s*", "", text, count=1, flags=re.S)
    return meta + text.rstrip() + "\n"


def extract_card_meta(text: str) -> str | None:
    match = re.search(r"<!--\s*tarot-cards:\s*(.*?)\s*-->", text)
    return match.group(1).strip() if match else None


def save(
    day: str,
    count: int,
    markdown: str,
    fingerprint: str,
    *,
    yes: bool = False,
) -> Path:
    """Keep history. Same cards → ask overwrite latest twin; different → always new file."""
    year, month, _ = day.split("-")
    directory = DATA_ROOT / "questions" / year / month
    directory.mkdir(parents=True, exist_ok=True)
    body = with_card_meta(markdown, fingerprint)
    timestamp = datetime.now().strftime("%H%M%S")
    destination = directory / f"{day}-{timestamp}-{count}cards.md"

    same_files = []
    for path in sorted(directory.glob(f"{day}-*-{count}cards.md")):
        try:
            meta = extract_card_meta(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if meta == fingerprint:
            same_files.append(path)

    if same_files:
        latest = same_files[-1]
        if yes or input(f"Same spread already saved today as {latest.name}. Overwrite? [y/N]: ").strip().lower() == "y":
            latest.write_text(body, encoding="utf-8")
            print(f"Overwrote same-spread file: {latest}")
            return latest
        print("Keeping old file; saving a new copy.")
    else:
        peers = list(directory.glob(f"{day}-*-{count}cards.md"))
        if peers:
            print(f"Different spread than earlier today; new file: {destination.name}")

    destination.write_text(body, encoding="utf-8")
    return destination


def parse_cli(argv: list[str]) -> dict[str, object]:
    flags = [arg for arg in argv[1:] if arg.startswith("-")]
    positionals: list[str] = []
    question: str | None = None
    seed: str | None = None
    i = 0
    args = argv[1:]
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
        if arg.startswith("-"):
            i += 1
            continue
        positionals.append(arg)
        i += 1
    if not positionals:
        raise RuntimeError("Usage: question_agent.py <3|5> [YYYY-MM-DD] [--draw] [-q question]")
    count = int(positionals[0])
    day = positionals[1] if len(positionals) > 1 else date.today().isoformat()
    return {
        "count": count,
        "day": day,
        "offline": "--offline" in flags,
        "draw": "--draw" in flags or "--auto" in flags,
        "yes": "--yes" in flags or "-y" in flags,
        "question": question,
        "seed": seed,
    }


def confirm_spread(plan: dict[str, object], *, yes: bool = False) -> None:
    from deck import format_drawn

    print("\nConfirm spread:")
    print(
        format_drawn(
            [
                {
                    "card_zh": c["card_zh"],
                    "card_en": c["card_en"],
                    "orientation": c["orientation"],
                }
                for c in plan["cards"]
            ],
            [str(c["position"]) for c in plan["cards"]],
        )
    )
    if yes:
        return
    answer = input("Generate now? [Y/n]: ").strip().lower()
    if answer in ("n", "no"):
        raise RuntimeError("Cancelled")


def main() -> int:
    try:
        opts = parse_cli(sys.argv)
        count = int(opts["count"])
        if count not in POSITIONS:
            raise RuntimeError("Only 3-card or 5-card spreads are supported")
        day = str(opts["day"])
        date.fromisoformat(day)
        offline = bool(opts["offline"])
        ensure_venv_python(need_web=not offline)

        from research import gather_for_spread

        data = collect(
            day,
            count,
            draw=bool(opts["draw"]),
            question=opts["question"] if isinstance(opts["question"], str) else None,
            seed=opts["seed"] if isinstance(opts["seed"], str) else None,
        )
        print("\n1/4 Local corpus + blog…")
        plan = resolve_reading(data)
        confirm_spread(plan, yes=bool(opts["yes"]))

        print("\n2/4 Web search (cached)…")
        if offline:
            print("  --offline: skipping web")
        research = gather_for_spread(plan["cards"], offline=offline)
        print(f"  Blog excerpts: {len(research['local_sources'])} 篇")
        print(f"  Web sources: {len(research['web_refs'])} 篇（{research['web_from']}）")

        print("\n3/4 Per-card readings…")
        per_card: dict[str, dict[str, str]] = {}
        keywords: dict[str, str] = {}
        for item in plan["cards"]:
            pos = str(item["position"])
            print(f"  · {pos}｜{item['card_zh']} {item['orientation']}")
            result = generate_one_card(
                data,
                item,
                plan["cards"],
                research["web_refs"],
            )
            per_card[pos] = result
            keywords[pos] = result["keywords"]

        print("\n4/4 Synthesis + Markdown…")
        synthesis = generate_synthesis(data, plan, per_card)
        payload = {
            **synthesis,
            "keywords": keywords,
            "per_card": {pos: piece["reading"] for pos, piece in per_card.items()},
        }
        markdown = assemble_markdown(
            data,
            plan,
            payload,
            research["web_refs"],
            research["local_sources"],
        )
        destination = save(
            day,
            count,
            markdown,
            spread_fingerprint(plan),
            yes=bool(opts["yes"]),
        )
        print("\n" + "=" * 72)
        print(markdown)
        print("=" * 72)
        print(f"\nSaved: {destination}")
        return 0
    except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
