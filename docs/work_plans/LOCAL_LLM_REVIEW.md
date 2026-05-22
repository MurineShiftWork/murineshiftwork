# Local LLM Code Review with vLLM

How to run the prompts in `CODE_REVIEW.md` locally using a GPU-backed vLLM server
instead of a cloud LLM or GitHub Actions.

---

## Model recommendations by hardware

### RTX 5090 — single GPU, 32 GB VRAM (this machine)

Key constraint: KV cache grows linearly with context length on top of model weights.
`Total VRAM = weights + KV cache`. Gemma 3's sliding-window attention keeps KV cache
much smaller than the naive estimate.

| Model | Quant | Weights | KV @ 32k | KV @ 64k | Verdict |
|---|---|---|---|---|---|
| `Qwen/Qwen2.5-Coder-32B-Instruct` | Q4_K_M | ~19 GB | ~8.5 GB | ~17 GB | Best code quality; **32k only** — 64k won't fit |
| `google/gemma-3-27b-it` | Q4_K_M | ~16 GB | ~4 GB | ~8 GB | Fits at 64k; sliding-window KV efficient; strong reasoning |
| `mistralai/Mistral-Small-3.1-24B-Instruct` | Q4_K_M | ~14 GB | ~5 GB | ~10 GB | Fits at 64k; 128k native context |
| `Qwen/Qwen2.5-Coder-14B-Instruct` | Q4_K_M | ~9 GB | ~5 GB | ~10 GB | Best 64k option; purpose-built for code; comfortable headroom |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | Q4_K_M | ~9 GB | ~5 GB | ~10 GB | Reasoning model; good for architecture and protocol review |

**Default choice:** `Qwen2.5-Coder-14B` for 64k reviews (task files whole);
`Qwen2.5-Coder-32B` at 32k for diff-only PR reviews where quality matters most.

### Multi-GPU (2+ A40 / A100)

| Model | Context | Notes |
|---|---|---|
| `Qwen/Qwen2.5-Coder-72B-Instruct` | 128k | Best code reasoning; needs ~80 GB VRAM (2×A100 or 4×A40) |
| `Qwen/Qwen2.5-Coder-32B-Instruct` | 128k | Fits 2×A40; quality close to 72B for focused reviews |
| `deepseek-ai/DeepSeek-Coder-V2-Instruct` | 128k | Strong on hardware-interface and multi-file audits |

---

## Start the vLLM server

### RTX 5090 — 32k context (best quality, diff reviews)

```bash
vllm serve Qwen/Qwen2.5-Coder-32B-Instruct \
    --max-model-len 32768 \
    --port 8000
```

### RTX 5090 — 64k context (whole-file reviews)

```bash
# Best balance of quality and context
vllm serve Qwen/Qwen2.5-Coder-14B-Instruct \
    --max-model-len 65536 \
    --port 8000

# Higher quality at 64k (sliding-window KV)
vllm serve google/gemma-3-27b-it \
    --max-model-len 65536 \
    --port 8000
```

### Multi-GPU (tensor parallelism)

```bash
vllm serve Qwen/Qwen2.5-Coder-72B-Instruct \
    --tensor-parallel-size 2 \
    --max-model-len 65536 \
    --port 8000
```

Server is ready when you see `Uvicorn running on http://0.0.0.0:8000`.
The API is OpenAI-compatible at `http://localhost:8000/v1/chat/completions`.

### Ollama (simpler, no manual quant selection)

```bash
# 14B — fits 64k on 5090
ollama pull qwen2.5-coder:14b
ollama serve   # starts on localhost:11434

# 32B — fits 32k on 5090
ollama pull qwen2.5-coder:32b
```

Ollama exposes an OpenAI-compatible endpoint at `http://localhost:11434/v1`.
Set `LLM_URL=http://localhost:11434/v1` in the review script below to use it.

---

## Run CI locally

CI has two workflows:

### 1. Lint (`.github/workflows/CI.yaml`)

Runs `pre-commit` on all files: ruff, ruff-format, mypy, gitleaks, commitizen.

```bash
# Install pre-commit hooks once
pre-commit install

# Run everything (same as CI)
pre-commit run --all-files
```

Individual tools without pre-commit:

```bash
ruff check src/ tests/              # lint
ruff format --check src/ tests/    # format check
mypy src/                           # type check (excludes external/)
```

### 2. Tests (`.github/workflows/install_and_test.yaml`)

```bash
# Hardware-dependent tests are skipped in CI via MSW_CI=1
MSW_CI=1 pytest tests/ -v --no-header -q

# With coverage
MSW_CI=1 pytest tests/ --cov=murineshiftwork --cov-report=term-missing

# Single test file
MSW_CI=1 pytest tests/test_sequence_writeback.py -v
```

Namespace readiness checks (from the `namespace-check` CI job):

```bash
python -c "
from pathlib import Path, import murineshiftwork
tasks_init = Path(list(murineshiftwork.__path__)[0]) / 'tasks' / '__init__.py'
assert not tasks_init.exists(), f'FAIL: {tasks_init} exists'
print('OK: tasks/__init__.py absent')
"
```

---

## Run LLM review locally (CI-style)

Assumes vLLM is running on port 8000. Set `LLM_URL` to switch to Ollama.

### Quick diff review (Prompt #1 — every PR)

```bash
export LLM_URL="${LLM_URL:-http://localhost:8000/v1}"
export LLM_MODEL="${LLM_MODEL:-Qwen/Qwen2.5-Coder-32B-Instruct}"

git diff main...HEAD | python3 - << 'EOF'
import sys, json, urllib.request, os

diff = sys.stdin.read()
if not diff.strip():
    print("No diff against main."); sys.exit(0)

prompt = open("docs/work_plans/CODE_REVIEW.md").read().split("```")[1]
payload = json.dumps({
    "model": os.environ["LLM_MODEL"],
    "messages": [
        {"role": "system", "content": "Expert Python reviewer for a Bpod-based neuroscience task controller."},
        {"role": "user", "content": f"{prompt}\n\n---\n\n{diff}"}
    ],
    "temperature": 0.1,
    "max_tokens": 4096,
}).encode()

req = urllib.request.Request(
    f"{os.environ['LLM_URL']}/chat/completions",
    data=payload,
    headers={"Content-Type": "application/json"},
)
resp = json.loads(urllib.request.urlopen(req, timeout=300).read())
print(resp["choices"][0]["message"]["content"])
EOF
```

### Whole-file review (start 64k server first)

```bash
export LLM_URL="${LLM_URL:-http://localhost:8000/v1}"
export LLM_MODEL="${LLM_MODEL:-Qwen/Qwen2.5-Coder-14B-Instruct}"

# Pick a prompt from CODE_REVIEW.md by number (1-10)
PROMPT_NUM=9   # task protocol correctness
FILE="src/murineshiftwork/tasks/sequence/task_objects.py"

python3 - << EOF
import json, urllib.request, os, re

prompts = re.split(r'\n## \d+\.', open("docs/work_plans/CODE_REVIEW.md").read())
prompt = prompts[${PROMPT_NUM}].split("```")[1] if len(prompts) > ${PROMPT_NUM} else prompts[-1]
content = open("${FILE}").read()

payload = json.dumps({
    "model": os.environ["LLM_MODEL"],
    "messages": [
        {"role": "system", "content": "Expert Python reviewer for a Bpod-based neuroscience task controller."},
        {"role": "user", "content": f"{prompt}\n\n---\n\n# {os.path.basename('${FILE}')}\n\n{content}"}
    ],
    "temperature": 0.1,
    "max_tokens": 4096,
}).encode()

req = urllib.request.Request(
    f"{os.environ['LLM_URL']}/chat/completions",
    data=payload,
    headers={"Content-Type": "application/json"},
)
resp = json.loads(urllib.request.urlopen(req, timeout=300).read())
print(resp["choices"][0]["message"]["content"])
EOF
```

### Combined: lint → test → LLM review

```bash
#!/usr/bin/env bash
set -e

export LLM_URL="${LLM_URL:-http://localhost:8000/v1}"
export LLM_MODEL="${LLM_MODEL:-Qwen/Qwen2.5-Coder-32B-Instruct}"

echo "=== pre-commit ==="
pre-commit run --all-files

echo "=== tests ==="
MSW_CI=1 pytest tests/ -q --no-header

echo "=== LLM diff review ==="
git diff main...HEAD | python3 - << 'PYEOF'
import sys, json, urllib.request, os
diff = sys.stdin.read()
if not diff.strip():
    print("No diff."); sys.exit(0)
prompt = open("docs/work_plans/CODE_REVIEW.md").read().split("```")[1]
payload = json.dumps({
    "model": os.environ["LLM_MODEL"],
    "messages": [
        {"role": "system", "content": "Expert Python reviewer for a Bpod-based neuroscience task controller."},
        {"role": "user", "content": f"{prompt}\n\n---\n\n{diff}"}
    ],
    "temperature": 0.1,
    "max_tokens": 4096,
}).encode()
req = urllib.request.Request(
    f"{os.environ['LLM_URL']}/chat/completions",
    data=payload,
    headers={"Content-Type": "application/json"},
)
resp = json.loads(urllib.request.urlopen(req, timeout=300).read())
print(resp["choices"][0]["message"]["content"])
PYEOF
```

Save this as `scripts/local_review.sh` and run with:

```bash
# Using vLLM on 5090
LLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct bash scripts/local_review.sh

# Using Ollama
LLM_URL=http://localhost:11434/v1 LLM_MODEL=qwen2.5-coder:32b bash scripts/local_review.sh
```

---

## Which prompts to prioritise

| Prompt | Title | Best used for |
|---|---|---|
| **#1** | General correctness and style | Every PR — run on the diff |
| **#3** | Hardware interface safety | Any change touching Bpod, valves, serial |
| **#4** | Session data integrity | Changes to readers, writers, namespace |
| **#9** | Task logic correctness | Changes to task_objects.py, state machines |
| **#2** | Platform compatibility | Cross-platform work (Windows/Linux) |

---

## Practical limits

- Keep total tokens (prompt + file) under `max-model-len - 4096` (reserve for output).
- For very large reviews split by module: task_objects.py separately from sequence.py.
- Temperature 0.1 gives stable, reproducible reviews; 0.0 can cause refusal on long inputs.
- vLLM loads the full model on startup — first request after start may take 30–60 s.
- Ollama keeps the model in memory between requests; first request warm-up only.

---

## Wiring to CI (future)

The prompts are designed to be CI-runnable. When a self-hosted GPU runner is available:
1. Add a `review.yaml` GitHub Actions workflow triggered on `pull_request`.
2. Start vLLM as a service step, POST the PR diff, post the response as a PR comment.
3. Gate merge only if reviewer finds `severity: high` issues (parse structured output).

This is not yet implemented — prompts exist in `CODE_REVIEW.md`, runner does not.
