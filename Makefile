.PHONY: setup backend frontend dev test demo lint

setup:
	cd backend && uv venv .venv && VIRTUAL_ENV=.venv uv pip install -e ".[dev]"
	cd frontend && npm install
	@test -f .env || cp .env.example .env

backend:
	cd backend && .venv/bin/python -m uvicorn outlier.main:app --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Open two terminals: 'make backend' and 'make frontend' (or use docker compose up)."

test:
	cd backend && .venv/bin/python -m pytest -q

demo:
	curl -s -X POST http://127.0.0.1:8000/api/demo/run | head -c 600; echo

lint:
	cd backend && .venv/bin/ruff check outlier tests
