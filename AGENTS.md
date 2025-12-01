# Repository Guidelines

## Project Structure & Module Organization
- Core app entrypoint lives in `app.py`; configuration is centralized in `config.py`.
- HTTP handlers are grouped in `routes/` (auth, admin, API, opt-out) and business logic in `services/`.
- Data access helpers sit in `models/` and `utils/database.py`; shared utilities (censoring, rate limits, Discord) live in `utils/`.
- Templates reside in `templates/` with static assets in `static/`; docs for integrations are under `docs/`.
- Tests belong in `tests/` (`test_*.py`). Keep new scripts alongside existing tools (e.g., `generate_opt_out_links.py`, `import_users.py`) in the repo root.

## Build, Test, and Development Commands
- Install deps: `pip install -r requirements.txt` (recommend a venv).
- Run the app locally: `python app.py` (reads `.env` or environment variables; defaults to dev mode).
- Containerized run: `docker-compose up --build` to start the web app (and Discord bot if enabled) on port 3000.
- Lint/format: no enforced tool in repo; if adding one, document it in this file and CI.
- Tests: `python -m pytest` from the repo root.

## Coding Style & Naming Conventions
- Follow Python PEP 8 (4-space indentation, snake_case for functions/modules, PascalCase for classes).
- Keep route handlers thin; put validation/business rules in `services/` or `models/`.
- Prefer explicit imports and type hints for new code; keep docstrings concise and action-oriented.
- Avoid committing secrets; load configuration from `.env` (copy from `.env.example`) or environment variables.

## Testing Guidelines
- Use `pytest`; place new tests under `tests/` mirroring module names (`tests/test_auth.py` style).
- Cover happy path and failure cases for new routes/services; mock external calls (Google, Discord, PostHog) rather than hitting live APIs.
- When adding DB changes, include a lightweight fixture or helper to set up/tear down temp tables if needed.

## Commit & Pull Request Guidelines
- Commit history favors short, present-tense summaries (e.g., `use workos for auth`). Keep messages imperative and under ~72 characters.
- For PRs, include: goal/summary, key changes, how to run/verify (`python app.py`, `python -m pytest`), and any schema or .env updates.
- Add screenshots or curl examples for UI/API changes; link related issues/tickets where applicable.

## Security & Configuration Tips
- Set `SECRET_KEY` and OAuth/Discord tokens via environment variables; never commit secrets or `users.db`.
- Production expects `PROD=TRUE` and HTTPS; review CSP and rate-limit settings in `app.py` when exposing new endpoints.
