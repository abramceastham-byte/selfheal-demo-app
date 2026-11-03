# Demo app: product reviews

Small FastAPI + SQLite app used as the target for the self-healing tool.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload     # http://localhost:8000
pytest
```

Set `SENTRY_DSN` to enable Sentry (see `.env.example`). Railway uses the `Procfile` / `railway.json` start command.

The workflow in `.github/workflows/test.yml` runs when this folder is its own repo root (the usual setup when connecting it to the tool).
