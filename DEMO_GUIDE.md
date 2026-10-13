# Demo Guide — AI Complexity Analyzer

## Quick Launch

```bash
cd AI_Complexity_Analyzer
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Open: http://localhost:8000
```

---

## Demo Flow (5-Minute Walkthrough)

### 1. Show Constant Time — O(1)

Click **Examples → Constant — Array head access**

- Analyze → Time: `O(1)`, Space: `O(1)`, High confidence
- Point out: no loops, no recursion detected in Static Evidence

---

### 2. Show Linear Time — O(n)

Click **Examples → Linear — Array sum**

- Analyze → Time: `O(n)`, Space: `O(1)`
- Show evidence: **1 loop**, max nesting depth 1

---

### 3. Show Quadratic Time — O(n²)

Click **Examples → Quadratic — Bubble sort**

- Analyze → Time: `O(n²)`, Space: `O(1)`
- Show evidence: **Nested loops detected at depth 2**
- Show Growth Chart → O(n²) curve highlighted in orange

---

### 4. Show Logarithmic Time — O(log n)

Click **Examples → Logarithmic — Binary search**

- Analyze → Time: `O(log n)`, Space: `O(1)`
- Show: best case `O(1)`, worst case `O(log n)`

---

### 5. Show Merge Sort — O(n log n)

Click **Examples → Linearithmic — Merge sort**

- Analyze → Time: `O(n log n)`, Space: `O(n)`
- Point out: recursion + sorting detected, space is O(n) due to auxiliary arrays

---

### 6. Show Exponential — O(2ⁿ)

Click **Examples → Exponential — Naive Fibonacci**

- Analyze → exponential candidate
- Contrast with **Memoized Fibonacci** → O(n) time

---

### 7. File Upload Demo

- Click **Upload** → select `examples/python_binary_search.py`
- Filename is auto-detected as Python
- Analyze → O(log n) result

---

### 8. Unsupported Language Demo

Paste this Go code:
```go
func linearSearch(arr []int, target int) int {
    for i, v := range arr {
        if v == target {
            return i
        }
    }
    return -1
}
```
- Select **Language: Auto-detect** → should detect or fall back to generic
- Still produces a result — shows resilience

---

## API Demo (curl)

```bash
# Health check
curl http://localhost:8000/api/health | python3 -m json.tool

# Language detection
curl -X POST http://localhost:8000/api/detect-language \
  -H "Content-Type: application/json" \
  -d '{"code": "def f(n):\n    for i in range(n): pass", "filename": "test.py"}'

# Analyze code
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def bubble_sort(arr):\n    for i in range(len(arr)):\n        for j in range(len(arr)-i-1):\n            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]",
    "language": "python"
  }' | python3 -m json.tool

# Upload file
curl -X POST http://localhost:8000/api/analyze-file \
  -F "file=@examples/python_merge_sort.py"
```

---

## Interactive API Docs

Open **http://localhost:8000/docs** for the Swagger UI — every endpoint is documented and executable.

---

## Enable AI Mode

```bash
# Edit .env
AI_PROVIDER=openai
AI_API_KEY=sk-your-key-here
AI_MODEL=gpt-4o-mini   # or gpt-4o, claude-3-haiku, etc.

# Restart server
uvicorn app.main:app --reload --port 8000
```

Status badge in the top-right corner will turn **purple** (AI mode) instead of yellow (fallback).
