.PHONY: help mypy ruff ruff-fix test

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

mypy: ## Run mypy strict type checking on src/
	uv run mypy src/

ruff: ## Run ruff linter
	uv run ruff check

ruff-fix: ## Run ruff check --fix
	uv run ruff check --fix

test: ruff mypy ## Run ruff, mypy, then pytest
	uv run pytest
