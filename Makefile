.PHONY: install lint format typecheck test check run up down logs

install:
	python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

format:
	.venv/bin/ruff format .
	.venv/bin/ruff check --fix .

typecheck:
	.venv/bin/mypy bot config quotes

test:
	.venv/bin/pytest

check: lint typecheck test

run:
	.venv/bin/python -m bot.main

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100
