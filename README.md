# aws-sqs-batchlib for Python

Consume and process Amazon SQS queues in large batches.

## Features

* Customizable batch size and batch window to consume and process messages
  in larger (> 10 message) batches. Collect up-to 10,000 messages from a queue
  and process them in one go.

## Installation

Install from PyPI with pip

```
pip install aws-sqs-batchlib
```

or with the package manager of choice.

## Usage

```python
import aws_sqs_batchlib

# Consume up-to 100 messages from the given queue, polling the queue for
# up-to 1 second to fill the batch.
res = aws_sqs_batchlib.consume(
    queue_url = "https://sqs.eu-north-1.amazonaws.com/123456789012/MyQueue",
    batch_size=100,
    maximum_batching_window_in_seconds=1,
    VisibilityTimeout=300,
)

# Returns messages in the same format as boto3 / botocore SQS Client
# receive_message() method.
assert res == {
    'Messages': [
        {'MessageId': '[.]', 'ReceiptHandle': 'AQ[.]JA==', 'MD5OfBody': '[.]', 'Body': '[.]'},
        {'MessageId': '[.]', 'ReceiptHandle': 'AQ[.]wA==', 'MD5OfBody': '[.]', 'Body': '[.]'}
        # ... up-to 1000 messages
    ]
}
```

## Development

Requires Python 3 and Poetry. Useful commands:

```bash
# Run tests
poetry run tox -e test

# Run linters
poetry run tox -e lint

# Format code
poetry run tox -e format
```

## Benchmarks & Manual Testing

Use `benchmark/benchmark.py` to benchmark and test the library functionality and performance. Execute following commands in Poetry virtualenv (execute `poetry shell` to get there):

```bash
# Setup
export PYTHONPATH=$(pwd)
export AWS_DEFAULT_REGION=eu-north-1

# Send messages to a queue
python3 benchmark/benchmark.py \
  --queue-url https://sqs.eu-north-1.amazonaws.com/123456789012/MyQueue producer

# Consume messages with the plain SQS ReceiveMessage polling
python3 benchmark/benchmark.py \
  --queue-url https://sqs.eu-north-1.amazonaws.com/123456789012/MyQueue consumer-plain

# Consume messages with the libary
python3 benchmark/benchmark.py \
  --queue-url https://sqs.eu-north-1.amazonaws.com/123456789012/MyQueue consumer-lib \
  --batch-size 1000
  --batch-window 1
```

Single thread is able to receive / send around 400 messages per second to an SQS queue on the same AWS region (eu-north-1, m5.large instance).

## License

MIT.