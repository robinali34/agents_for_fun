#!/usr/bin/env python3
"""Collect a daily fitness log, analyze it with local Ollama, and save Markdown."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:7b"


def ask(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{label}{suffix}: ").strip()
    return answer or default


def collect() -> dict[str, str]:
    print("\n每日减脂记录（不清楚可留空）\n")
    return {
        "date": ask("日期", date.today().isoformat()),
        "weight_lb": ask("晨起体重（磅）"),
        "waist": ask("腰围 cm"),
        "sleep": ask("睡眠时长/质量"),
        "steps": ask("今日步数"),
        "training": ask("训练内容与时长"),
        "food": ask("饮食概况"),
        "protein": ask("蛋白质摄入（克或食物描述）"),
        "water": ask("饮水量"),
        "hunger": ask("饥饿感 1-10"),
        "energy": ask("精神/体能 1-10"),
        "pain": ask("疼痛或不适部位及程度"),
        "notes": ask("其他记录"),
    }


def make_prompt(data: dict[str, str]) -> str:
    values = "\n".join(f"- {key}: {value or '未记录'}" for key, value in data.items())
    return f"""你是一位谨慎、务实的健身记录助手，目标是帮助用户可持续减脂。

根据以下单日记录生成 Markdown 日报：
{values}

要求：
1. 只输出 Markdown，不使用代码围栏。
2. 保留用户的原始数据，不虚构热量、营养或身体指标。
3. 单日体重波动不能被解释为脂肪增减；体重单位为磅（lb），没有多日数据时明确说明趋势不足。
4. 建议必须具体、温和、可执行，避免极端节食和惩罚性训练。
5. 疼痛不为零或描述异常时，建议降低训练强度；若有胸痛、晕厥、呼吸困难或剧烈/持续疼痛，明确建议停止训练并及时求医。
6. 不做医学诊断。

使用以下结构：
# 健身日报｜{data['date']}
## 今日数据
## 训练与活动
## 饮食与恢复
## 今日分析
## 明日建议
## 风险与注意事项
## 原始记录
## 标签
"""


def analyze(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": "使用简体中文回答。"},
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
        raise RuntimeError(f"无法连接 Ollama：{exc}") from exc
    return result["message"]["content"].strip()


def save(day: str, markdown: str) -> Path:
    year, month, _ = day.split("-")
    directory = ROOT / "daily" / year / month
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{day}.md"
    if destination.exists():
        answer = input(f"{destination} 已存在，覆盖？[y/N]: ").strip().lower()
        if answer != "y":
            raise RuntimeError("已取消，原文件未修改")
    destination.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    return destination


def main() -> int:
    try:
        data = collect()
        print("\n正在用本地模型分析，请稍候……")
        markdown = analyze(make_prompt(data))
        destination = save(data["date"], markdown)
        print(f"\n已保存：{destination}")
        return 0
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"\n错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
