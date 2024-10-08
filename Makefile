## Build targets
.PHONY: lint test format lint-pylint lint-black lint-mypy lint-bandit
test:
	poetry run pytest -vv --log-level=DEBUG --cov aws_sqs_batchlib --cov-report term-missing

lint: lint-ruff-check lint-ruff-format lint-mypy lint-bandit
lint-ruff-check:
	poetry run ruff check
lint-ruff-format:
	poetry run ruff format --check
lint-mypy:
	poetry run mypy aws_sqs_batchlib benchmark
lint-bandit:
	poetry run bandit -q -r aws_sqs_batchlib benchmark

format:
	poetry run ruff format
	poetry run ruff check --fix