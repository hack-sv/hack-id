# CRUSH.md

Build/lint/test
- Install: python -m pip install -r requirements.txt
- Run app (dev): python app.py
- Run bot: python discord_bot.py
- DB init: python utils/db_init.py
- Tests (if tests/ exists): python -m pytest -q
- Single test file:: python -m pytest -q tests/test_file.py -k "name"
- Lint (ruff, if installed): ruff check .
- Format (ruff+black, if installed): ruff format . || black .

Conventions
- Python 3.8+; Flask app entry: app.py; configuration in config.py; services/ encapsulate business logic; routes/ define Blueprints; models/ are simple data containers; utils/ shared helpers.
- Imports: standard lib, third-party, local; absolute imports preferred; no circular deps; from X import Y only for localized symbols.
- Formatting: PEP 8; 88–100 char lines; ruff/black compatible; no inline comments with secrets; keep template/JS/CSS assets under static/ and templates/.
- Types: use typing and pydantic where present; annotate public functions; prefer Optional/Tuple/Dict over Any; validate external inputs in utils/validation.py or services/.
- Naming: snake_case for vars/functions; PascalCase for classes; UPPER_SNAKE for constants/env keys; template IDs/classes kebab-case.
- Errors: never leak secrets; raise/return Flask abort with proper HTTP codes; centralize handlers in utils/error_handling.py; log minimal context.
- Security: load env via python-dotenv; never commit .env; CSRF and session config via Flask/WTForms; rate limiting via Flask-Limiter (disabled in dev) per README.
- Database: created on first run; management scripts in utils/ and root scripts; avoid schema changes in request path.
- APIs: Bearer auth for /api; respect permissions.json; avoid breaking changes; version-sensitive changes behind new routes.
- Frontend: keep admin JS in static/scripts/admin; styles in static/styles; do not inline large scripts/styles in templates.

Notes
- No Cursor or Copilot rule files found.
- Add commonly used commands here as they evolve.
