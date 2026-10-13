# AI-Based Complexity Prediction Tool

> **Academic University Project** — A locally-runnable tool that predicts algorithmic time and space complexity using static code analysis combined with an optional AI language model.

---

## Overview

This tool allows developers and students to:
1. Paste or upload source code in 30+ programming languages
2. Receive time and space complexity predictions in Big-O notation
3. View best-, average-, and worst-case analysis
4. Explore complexity growth visualizations
5. Get AI-powered optimization suggestions
6. Understand the evidence behind each prediction

---

## Quick Start

```bash
# 1. Clone or navigate to project folder
cd AI_Complexity_Analyzer

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env to add your AI API key (optional — works without one)

# 5. Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Open in browser
open http://localhost:8000
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AI_PROVIDER` | `mock` | `openai`, `mock` |
| `AI_API_KEY` | *(empty)* | API key for the AI provider |
| `AI_MODEL` | `gpt-4o-mini` | Model identifier |
| `AI_BASE_URL` | OpenAI URL | Override for compatible APIs |
| `AI_TIMEOUT_SECONDS` | `30` | Request timeout |
| `AI_MAX_RETRIES` | `2` | Retry attempts |
| `MAX_CODE_SIZE_KB` | `512` | Maximum code upload size |

**Without an API key:** The application runs in fallback mode using static analysis only. All static features work fully.

**With an API key:** Set `AI_PROVIDER=openai` and `AI_API_KEY=sk-...` in `.env`. AI-assisted explanations and optimizations are then enabled.

### Compatible AI Providers

The `AI_BASE_URL` can be overridden to use any OpenAI-compatible API:
- **Groq:** `https://api.groq.com/openai/v1`
- **Together AI:** `https://api.together.xyz/v1`
- **Mistral:** `https://api.mistral.ai/v1`
- **Local Ollama:** `http://localhost:11434/v1`

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Application health and version |
| `GET` | `/api/languages` | Supported language registry |
| `POST` | `/api/detect-language` | Detect language from code |
| `POST` | `/api/analyze` | Analyze code complexity (JSON) |
| `POST` | `/api/analyze-file` | Analyze uploaded file |
| `GET` | `/api/config/status` | Safe configuration status |
| `GET` | `/docs` | Interactive Swagger UI |

---

## Running Tests

```bash
source venv/bin/activate
pytest -v
```

Test coverage:
- Health and configuration endpoints
- Language detection (Python, JS, Java by extension and heuristics)
- Static analysis: O(1), O(n), O(n²), O(log n), recursion detection
- Analysis API: valid/invalid requests, file uploads, oversized input
- AI provider: mock fallback behavior
- Security: no code execution, no path traversal, no key exposure

---

## How Complexity Analysis Works

### Step 1: Language Detection
Uses file extension → Pygments lexer → keyword heuristics → user override.

### Step 2: Parsing
- **Python**: Python `ast` module — full AST analysis of loops, recursion, library calls.
- **All others**: Regex-based heuristic analysis of loop patterns, recursion hints, sorting calls.

### Step 3: Structural Analysis
Identifies: loops, nesting depth, recursion type, sorting, binary search, divide-and-conquer, memory allocations, early exits.

### Step 4: Rule-Based Inference
Applies evidence-based rules:
- No loops/recursion → O(1)
- Single loop traversing n → O(n)
- Two nested loops each over n → O(n²)
- Sorting call → O(n log n)
- Multiple recursive calls → O(2ⁿ) candidate
- Binary search pattern → O(log n)

### Step 5: AI Reasoning (when configured)
Sends structured evidence to the AI model. The model reviews the code, assesses the static findings, and returns a validated JSON response including explanation, cases, and optimizations.

### Step 6: Reconciliation
Static evidence and AI output are combined. AI explanations supplement static results; clear structural evidence takes priority over unsupported AI claims.

---

## Supported Languages

| Tier | Description | Languages |
|---|---|---|
| **Full Parser** | Python AST — highest accuracy | Python |
| **Heuristic** | Regex analysis — good for common patterns | JavaScript, TypeScript, Java, C++, C, C#, Go, Rust, Kotlin, Swift, Ruby, PHP, Scala, R, Julia, Dart, Lua, Perl, Haskell, Elixir, SQL, Bash, PowerShell, MATLAB, Fortran, COBOL, Solidity, Assembly, Erlang, Objective-C |
| **Generic** | Best-effort — for unrecognized languages | Any |

---

## Architecture

```
Browser (HTML/CSS/JS)
        ↓
FastAPI (app/main.py)
        ↓
API Routes (app/api/routes.py)
        ↓
Analysis Pipeline (app/core/analysis_pipeline.py)
    ├── Language Detection
    ├── Parser (Python AST / Generic Heuristic)
    ├── Complexity Rules
    ├── AI Provider (OpenAI-compatible / Mock)
    └── Result Reconciliation
```

---

## Security

- Submitted code is **never executed** (no `eval`, `exec`, `subprocess`).
- API keys stay on the backend — never sent to the browser.
- File uploads are sanitized, size-limited, and never stored.
- No stack traces are returned to the browser.
- AI-generated text is rendered as plain text (no unsafe HTML injection).

---

## Known Limitations

1. **Python-only AST parsing**: Other languages use heuristic regex analysis, which is less precise.
2. **AI estimates**: LLM predictions are not mathematically proven. They are educated estimates.
3. **Complex patterns**: Template metaprogramming, macros, dynamic dispatch, and closures may not be fully modeled.
4. **External library calls**: Complexity of external functions (e.g., NumPy operations) is not automatically known.
5. **SQL complexity**: Depends on query plans, indexes, data distribution, and database engine — not just syntax.
6. **Amortized complexity**: Not always reported; may be mentioned in AI explanations.
7. **Randomized algorithms**: Expected complexity may differ from worst-case.

---

## Future Improvements

- Tree-sitter parser integration for C, C++, Java, JavaScript
- Call graph analysis for library function complexity
- Recurrence relation solver (Master Theorem)
- Loop bound analysis from type information
- Historical comparison across multiple code submissions
- Batch file analysis mode

---

## Troubleshooting

**Server won't start:**
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Port already in use:**
```bash
uvicorn app.main:app --port 8001
```

**AI analysis not working:**
- Check `AI_API_KEY` in `.env`
- Verify `AI_PROVIDER=openai` (not `mock`)
- Check `/api/config/status` for current mode

**Tests fail with import errors:**
```bash
source venv/bin/activate
pip install -r requirements.txt
pytest -v
```
