# Apple DFT Workplace Assistant (Dify)

Personal **Chatflow** for settling into a **Senior Software Engineer** role focused on **Design-for-Test (DFT) for hardware** at Apple.

This is a **personal coach**, not an Apple-internal system. Keep confidential work in approved Apple tools only.

## What’s in this folder

| Path | Purpose |
|------|---------|
| `apple-dft-workplace-assistant.yml` | Importable Dify DSL (Chatflow) |
| `knowledge/*.md` | Starter knowledge docs for a Dify Knowledge Base |
| `README.md` | This guide |

Personal notes + **auto-saved plans**: `~/AI_Data/Workplace/AppleDFT/`

> **Important:** Dify Preview only *shows* Markdown. It does not write `~/AI_Data/.../*.md`.
> To generate a plan and save it automatically:
>
> ```bash
> ~/AI_Data/Workplace/AppleDFT/run.sh plan 30
> ```
>
> To save a reply you already got in Dify:
>
> ```bash
> ~/AI_Data/Workplace/AppleDFT/run.sh save 30
> ```

## Prerequisites

1. Dify running: `~/AI_Data/dify-up.sh` → http://localhost  
2. Ollama model configured in Dify (**Integrations → Model Provider → Ollama**), e.g. `qwen2.5:7b`  
   Base URL from containers: `http://172.17.0.1:11434` (not `127.0.0.1`)

## Install in Dify (about 5 minutes)

### 1. Import the app

1. Open http://localhost → **Studio**  
2. **Create from DSL** / **Import DSL**  
3. Choose:

```text
~/rli/agents_for_fun/infra/dify/apps/apple-dft-onboarding/apple-dft-workplace-assistant.yml
```

4. Open the app → confirm the **LLM** node uses **Ollama / `qwen2.5:7b`** → **Publish**

If you see **Internal Server Error** / `plugin not found` when chatting, the LLM node has no model selected. Fix: Orchestrate → LLM → Provider **Ollama** → Model **qwen2.5:7b** → Save → Publish.

### 2. (Recommended) Knowledge Base

1. **Knowledge** → Create dataset, e.g. `Apple-DFT-Onboarding`  
2. Upload all files from `knowledge/`  
3. In the Chatflow, enable **Context** on the LLM node and attach that dataset  
   (or add a Knowledge Retrieval node before LLM if you prefer an explicit graph)

Also copy docs into your personal tree if you want local edits:

```bash
cp -n ~/rli/agents_for_fun/infra/dify/apps/apple-dft-onboarding/knowledge/*.md \
  ~/AI_Data/Workplace/AppleDFT/knowledge/
```

### 3. Chat

Use the suggested prompts, or try:

- “Draft my first 30-day plan for this DFT Senior SWE role”
- “What should I ask my manager in week-1 1:1s?”
- “Build a DFT learning map for a software engineer new to hardware test”

## Privacy checklist

- Do **not** upload Apple-confidential PDFs, code, or specs into this knowledge base  
- Prefer high-level personal reflections in `~/AI_Data/Workplace/AppleDFT/notes/`  
- If you paste something sensitive by mistake, delete that chat and avoid re-uploading

## Customize

| Knob | Where |
|------|--------|
| System prompt | Chatflow → LLM node → system message |
| Opening / suggested questions | Features / Orchestrate UI |
| Temperature | LLM node (default `0.4`) |
| Model | LLM node (empty in DSL → pick after import) |

## Related

- Stack ops: `infra/dify/README.md`  
- Start stack: `~/AI_Data/dify-up.sh`
