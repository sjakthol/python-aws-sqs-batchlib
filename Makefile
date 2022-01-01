## Build targets
.PHONY: lint test format lint-pylint lint-black lint-mypy lint-bandit
test:
	poetry run pytest -vv --log-level=DEBUG --cov aws_sqs_batchlib --cov-report term-missing

lint: lint-pylint lint-black lint-mypy lint-bandit
lint-pylint:
	poetry run pylint --max-line-length=120 --score=n aws_sqs_batchlib tests
lint-black:
	poetry run black --check aws_sqs_batchlib tests benchmark
lint-mypy:
	poetry run mypy aws_sqs_batchlib benchmark
lint-bandit:
	poetry run bandit -q -r aws_sqs_batchlib benchmark

format:
	poetry run black aws_sqs_batchlib tests benchmark