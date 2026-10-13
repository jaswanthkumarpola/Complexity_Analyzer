# AI Complexity Analyzer

A locally-run tool that predicts the time and space complexity (Big-O) of source code. It combines static code analysis with an AI model and explains the evidence behind each prediction.

## Features

- Paste or upload code in 30+ languages
- Time and space complexity, plus best/average/worst case
- AI explanation and optimization suggestions
- Complexity growth visualization
- Manual language selection is validated against the pasted code

## Quick Start

```bash
cd AI_Complexity_Analyzer
python3 -m venv venv
source venv/bin/activate         
pip install -r requirements.txt
cp .env.example .env              
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000. API docs are at http://localhost:8000/docs.

## Configuration (`.env`)

```dotenv
AI_PROVIDER=openai
AI_API_KEY=your_real_key_here
AI_MODEL=openai/gpt-oss-120b
AI_BASE_URL=https://api.groq.com/openai/v1
AI_TIMEOUT_SECONDS=30
AI_MAX_RETRIES=2
MAX_CODE_SIZE_KB=512
```

- Works with any OpenAI-compatible API (Groq, OpenAI, Together, Mistral, local Ollama). Change `AI_BASE_URL` and `AI_MODEL` to match your provider.
- If the key is missing or still a placeholder, analysis fails with a clear "AI provider is not configured" error. There is no silent fallback.
- `AI_PROVIDER=mock` gives static-only results (for demos and tests).
- **Restart the server after editing `.env`.** `--reload` does not re-read it.
- Never commit `.env`. It is listed in `.gitignore`.

## How It Works

1. Detect the language (or use your manual selection, which is validated)
2. Parse the code (Python AST; regex heuristics for other languages)
3. Apply rule-based complexity inference
4. Send the code and static evidence to the AI model
5. Return the AI estimate with static evidence as justification

## Input Validation

- If you select a language manually and the code clearly belongs to another one, the request is rejected with a 422 error such as "you selected Python, but the submitted code looks like JavaScript".
- AI failures (timeout, bad key, wrong model, malformed output) return a readable error instead of a guessed result.

## Security

- Submitted code is never executed.
- API keys stay on the backend and are never sent to the browser.
- Uploaded files are size-limited, sanitized, and not stored.

## Known Limitations

- Only Python uses full AST parsing; other languages use heuristics.
- AI estimates are educated guesses, not mathematical proofs.
- Macros, templates, dynamic dispatch, and external library calls are not fully modeled.

## Troubleshooting

- **AI not working:** check `AI_API_KEY`, `AI_MODEL`, `AI_BASE_URL`, restart the server, then open `/api/config/status` to see what was loaded.
- **HTTP 404 "model does not exist":** the model name is wrong or retired. List valid models from your provider's `/models` endpoint.
- **"rejected the API key":** create a new key.
- **Timed out:** raise `AI_TIMEOUT_SECONDS`.
- **Port in use:** `uvicorn app.main:app --port 8001`.

## Tests

```bash
pytest -v
```