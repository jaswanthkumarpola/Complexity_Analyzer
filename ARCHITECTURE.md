# Architecture Overview — AI Complexity Analyzer

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│  HTML/CSS/JS  ─  No frameworks, Vanilla ES2022             │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────┐    │
│  │  Code Editor    │    │   Results Dashboard          │    │
│  │  (editor.js)    │    │   (results.js + charts.js)  │    │
│  └────────┬────────┘    └─────────────┬───────────────┘    │
│           │                           │                     │
│           └──────────┬────────────────┘                     │
│                      │ api.js (fetch wrapper)               │
└──────────────────────┼──────────────────────────────────────┘
                       │ HTTP (JSON/multipart)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Application                        │
│                   (app/main.py)                              │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              API Layer (app/api/)                    │  │
│  │                                                      │  │
│  │  routes.py        schemas.py                         │  │
│  │  /health          Request/Response Pydantic models   │  │
│  │  /languages       Validation (422, 413 errors)       │  │
│  │  /detect-language                                    │  │
│  │  /analyze                                            │  │
│  │  /analyze-file                                       │  │
│  └───────────────────────┬──────────────────────────────┘  │
│                          │                                  │
│  ┌───────────────────────▼──────────────────────────────┐  │
│  │         Analysis Pipeline (app/core/)                │  │
│  │                                                      │  │
│  │  Step 1: Input validation   (utils/validation.py)   │  │
│  │  Step 2: Language detection (language_detection.py) │  │
│  │  Step 3: Code parsing       (parser_manager.py)     │  │
│  │  Step 4: Static heuristics  (static_analyzer.py)   │  │
│  │  Step 5: Rule inference     (complexity_rules.py)   │  │
│  │  Step 6: AI reasoning       (app/ai/)               │  │
│  │  Step 7: Reconciliation     (analysis_pipeline.py) │  │
│  │  Step 8: Visualization      (recurrence_analysis.py)│  │
│  └───────────────────────┬──────────────────────────────┘  │
│                          │                                  │
│  ┌───────────────────────▼──────────────────────────────┐  │
│  │             AI Provider Layer (app/ai/)              │  │
│  │                                                      │  │
│  │  base_provider.py — Abstract interface               │  │
│  │  llm_provider.py  — OpenAI-compatible HTTP client   │  │
│  │  mock_provider.py — Deterministic fallback           │  │
│  │  provider_factory.py — Environment-based selection  │  │
│  │  prompts.py       — Structured prompt templates     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Descriptions

### `app/api/`

| File | Purpose |
|---|---|
| `routes.py` | FastAPI route handlers; input size enforcement; error normalization |
| `schemas.py` | All Pydantic models: requests, responses, enums, nested models |

### `app/core/`

| File | Purpose |
|---|---|
| `analysis_pipeline.py` | 8-step orchestration — the central coordinator |
| `language_detection.py` | Multi-strategy detection: extension → heuristics → pygments → generic |
| `language_registry.py` | Single source of truth for 30+ supported languages |
| `parser_manager.py` | Python AST visitor — extracts loops, recursion, library calls, sorting |
| `static_analyzer.py` | Regex heuristic analyzer for non-Python languages |
| `complexity_rules.py` | Evidence → Big-O rule engine (no ML, pure logic) |
| `recurrence_analysis.py` | Growth curve data builder for Chart.js visualization |

### `app/ai/`

| File | Purpose |
|---|---|
| `base_provider.py` | Abstract base class defining the provider contract |
| `llm_provider.py` | OpenAI-compatible HTTP client; retry logic; JSON schema validation |
| `mock_provider.py` | Deterministic offline fallback; mirrors static analysis result |
| `provider_factory.py` | Reads `AI_PROVIDER` env; returns the appropriate provider |
| `prompts.py` | Structured prompt templates with few-shot examples |

### `app/utils/`

| File | Purpose |
|---|---|
| `validation.py` | Code size enforcement, filename sanitization, MIME type checks |
| `errors.py` | Centralized `APIError` with HTTP code mapping; no stack trace leaks |

### `app/static/`

| File | Purpose |
|---|---|
| `index.html` | Semantic HTML5; full accessibility (ARIA, roles); SEO meta tags |
| `css/styles.css` | Design system: design tokens, layout, components, responsive |
| `js/api.js` | Fetch wrapper for all backend API calls |
| `js/editor.js` | Code editor, line numbers, examples library, file upload |
| `js/charts.js` | Chart.js rendering; text fallback when CDN unavailable |
| `js/results.js` | DOM update functions for analysis results (XSS-safe) |
| `js/app.js` | Main controller; wires all modules; keyboard shortcuts |

---

## Data Flow

```
User submits code
       │
       ▼
routes.py: size check → 413 if > MAX_CODE_SIZE_KB
       │
       ▼
analysis_pipeline.py
       │
       ├─ 1. validate_input() → 422 on empty/whitespace
       │
       ├─ 2. detect_language()
       │      ├─ Extension match (High confidence)
       │      ├─ Keyword heuristics (Medium/High)
       │      └─ Pygments fallback (Low)
       │
       ├─ 3. parse_code()
       │      ├─ Python → ast.parse() → FeatureVisitor
       │      └─ Others → regex patterns in static_analyzer
       │
       ├─ 4. extract_evidence() → normalized dict
       │      {loops, nested_loops, recursive_functions,
       │       has_sorting, has_binary_search, ...}
       │
       ├─ 5. infer_complexity() → ComplexityInference
       │      Rule table:
       │      ├─ no loops, no recursion → O(1)
       │      ├─ 1 loop × n → O(n)
       │      ├─ 2 nested loops × n → O(n²)
       │      ├─ sort call → O(n log n)
       │      ├─ binary search pattern → O(log n)
       │      └─ multiple recursion → O(2ⁿ) candidate
       │
       ├─ 6. ai_provider.analyze() [if configured]
       │      ├─ Builds structured prompt
       │      ├─ Calls AI API with retry + timeout
       │      ├─ Validates JSON response schema
       │      └─ Falls back to static result on failure
       │
       ├─ 7. reconcile() → merged result
       │      AI explanation + static evidence structure
       │
       └─ 8. build_visualization() → growth curves for Chart.js
              {x_values, curves: {O(1): [...], O(n): [...], ...}}
```

---

## Language Detection Strategy

```
Priority:
1. user_selected → immediate, High confidence
2. file extension → get_language_by_extension(), High confidence
3. keyword heuristics → weighted keyword scoring per language
   - Each language has 5-8 distinctive keywords
   - Winner must have ≥40% share AND ≥1 hit
   - Confidence: High (≥3), Medium (2), Low (1)
4. pygments → guess_lexer() exact class name match, Medium confidence
5. generic fallback → identity Unknown confidence
```

**Why heuristics before pygments?**
`pygments.guess_lexer()` is optimized for tokenization, not short-snippet identification. For 5-30 line code samples without filenames, it frequently returns incorrect results (e.g., returning `ScdocLexer` for Python code). The keyword heuristics are purpose-built for the languages in our registry and are significantly more reliable.

---

## Security Model

| Threat | Mitigation |
|---|---|
| Code execution | No `eval`, `exec`, `subprocess`, `compile` used anywhere |
| Path traversal | Filenames sanitized; `os.path.basename` enforced |
| Oversized input | `MAX_CODE_SIZE_KB` enforced in both routes and validation |
| XSS | JS uses `textContent` (never `innerHTML`) for all user data |
| Secret leakage | API keys never sent to frontend; `/api/config/status` only exposes booleans |
| CORS | Configured in `main.py`; restrict in production |
| Prompt injection | Structured prompt keeps AI instructions separate from user code |
| DoS (regex) | Regex patterns are non-backtracking; size limit enforced before regex |

---

## AI Provider Contract

```python
class BaseProvider:
    async def analyze(
        code: str,
        language: str,
        static_summary: str,
    ) -> ProviderResult

@dataclass
class ProviderResult:
    time_complexity: str        # Big-O expression
    space_complexity: str       # Big-O expression
    explanation: str            # Human-readable reasoning
    best_case: str | None
    average_case: str | None
    worst_case: str | None
    assumptions: list[str]
    warnings: list[str]
    optimizations: list[dict]
    confidence: str             # High/Medium/Low
    is_fallback: bool
    provider: str
    model: str | None
    raw_response: str | None
```

---

## Adding a New Language

1. **Add to `language_registry.py`**: Create a `LanguageDefinition` entry with appropriate `identifier`, `extensions`, `keywords`, and `pygments_lexer`.
2. **Add keywords**: 5-8 distinctive patterns that appear in this language but not in similar ones.
3. **Extend static analyzer** (optional): Add regex patterns in `static_analyzer.py` if the language has distinctive loop/recursion syntax.
4. **Add examples** (optional): Create a file in `examples/` demonstrating complexity patterns.

---

## Performance

- Analysis pipeline: ~5-50ms (static only)
- AI API call: 1-5s depending on model and provider
- Visualization data: pre-computed, not rendered server-side
- No database, no cache: each request is fully stateless
