# 本地塔罗 Agent

用本机 Ollama + 本地韦特语料生成每日一抽 / 问题牌阵 Markdown。  
参考了开源项目的好用点：[tarot-oracle](https://github.com/k98kurz/tarot-oracle)、[2acrestudios/tarot](https://github.com/2acrestudios/tarot)、[arcanai](https://github.com/leahfrom/arcanai) —— **自动抽牌、问题一键开跑、生成前确认**。

## 快速开始

```bash
cd ~/AI_Data/Tarot
./tarot.sh                 # 交互菜单
./fetch-corpus.sh          # 首次构建本地 78 牌语料
```

一键示例（类似 `oracle "question" --interpret`）：

```bash
# 每日一抽：自动抽牌 + 指定问题 + 跳过确认
./tarot.sh daily --draw -q "今天注意什么" -y

# 三牌：自动抽 + 问题 + 离线
./tarot.sh 3 --draw -q "下周如何安排" -y --offline

# 五牌
./tarot.sh 5 --draw -q "项目卡点" -y
```

实体牌仍可手输：

```bash
./daily-one.sh
./question-3.sh
```

## 入口

| 命令 | 说明 |
|------|------|
| `./tarot.sh` | 统一菜单 |
| `./daily-one.sh` | 每日单牌 |
| `./question-3.sh` | 现状 / 阻碍 / 建议 |
| `./question-5.sh` | 五牌 |
| `./fetch-corpus.sh` | 重建语料 |

## 常用选项

| 选项 | 含义 |
|------|------|
| `--draw` / `--auto` | 从本地 78 张牌随机抽（含正逆） |
| `-q` / `--question` | 问题文本 |
| `--offline` | 不联网 |
| `-y` / `--yes` | 跳过确认与覆盖提问 |
| `--seed TEXT` | 可复现抽牌 |
| `YYYY-MM-DD` | 指定日期 |

## 流程

```text
提问 / 抽牌或手输
  → 语料校验（模糊匹配；未知牌名直接报错并给候选）
  → 确认牌阵（可用 -y 跳过）
  → 本地语料 +（可选）网络 cache
  → 逐牌解读（牌阵）/ 单牌生成
  → 保存 Markdown
```

## 保存规则

- **每日**：`YYYY/MM/YYYY-MM-DD.md`；同日不同牌 → 另存 `YYYY-MM-DD-HHMMSS.md`
- **问题牌阵**：`questions/YYYY/MM/YYYY-MM-DD-HHMMSS-{3|5}cards.md`
- 文件头带 `<!-- tarot-cards: ... -->` 指纹，用于判断是否同牌

## 目录

```text
~/AI_Data/Tarot/
├── tarot.sh              # 统一入口
├── deck.py               # 抽牌 / 模糊匹配
├── tarot_agent.py        # 每日一抽
├── question_agent.py     # 三/五牌
├── research.py           # 联网 + cache
├── corpus/waite-rws.json
└── questions/
```

## 注意

- 默认模型：`qwen2.5:7b`（可在 `tarot_agent.py` 改 `MODEL`）
- 塔罗用于自我觉察，不断言命运，不替代专业建议
- 非感情问题会尽量避免把圣杯牌默认解成恋爱
