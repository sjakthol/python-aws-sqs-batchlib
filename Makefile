## Build targets
.PHONY: lint test format lint-pylint lint-black lint-mypy lint-bandit
test:
	uv run pytest -vv --log-level=DEBUG --cov aws_sqs_batchlib --cov-report term-missing

lint: lint-ruff-check lint-ruff-format lint-mypy lint-bandit
lint-ruff-check:
	uv run ruff check
lint-ruff-format:
	uv run ruff format --check
lint-mypy:
	uv run mypy aws_sqs_batchlib benchmark
lint-bandit:
	uv run bandit -q -r aws_sqs_batchlib benchmark

format:
	uv run ruff format
	uv run ruff check --fix