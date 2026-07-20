# 本地健身记录 Agent

每天运行：

```bash
~/AI_Data/Fitness/run.sh
```

脚本会询问体重（磅）、腰围、睡眠、步数、训练、饮食、蛋白质、饮水、
饥饿感、精神状态和疼痛情况，随后使用本机 Ollama 的 `qwen2.5:7b`
生成分析。

日报保存在：

```text
daily/YYYY/MM/YYYY-MM-DD.md
```

周报预留目录：

```text
weekly/
```

这些分析用于记录和一般性建议，不替代医生、营养师或教练的专业判断。
