# aws-sqs-batchlib for Python

Consume and process Amazon SQS queues in large batches.

## Features

* Consume arbitrary number of messages from an Amazon SQS queue.

  * Define maximum batch size and batching window in seconds to consume a batch
    of messages from Amazon SQS queue similar to Lambda Event Source Mapping.

* Delete arbitrary number of messages from an Amazon SQS queue.


## Installation

Install from PyPI with pip

```
pip install aws-sqs-batchlib
```

or with the package manager of choice.

## Usage

### Consume

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

### Delete

```python
import aws_sqs_batchlib

# Delete an arbitrary number of messages from a queue
res = aws_sqs_batchlib.delete_message_batch(
    QueueUrl="https://sqs.eu-west-1.amazonaws.com/777907070843/test",
    Entries=[
        {"Id": "1", "ReceiptHandle": "<...>"},
        {"Id": "2", "ReceiptHandle": "<...>"},
        # ...
        {"Id": "175", "ReceiptHandle": "<...>"},
        # ...
    ],
)

# Returns result in the same format as boto3 / botocore SQS Client
# delete_message_batch() method.
assert res == {
    "Successful": [
        {"Id": "1"},
        # ...
    ],
    "Failed": [
        {
            "Id": "2",
            "SenderFault": True,
            "Code": "ReceiptHandleIsInvalid",
            "Message": "The input receipt handle is invalid.",
        }
    ],
}
```


## Development

Requires Python 3 and Poetry. Useful commands:

```bash
# Setup environment
poetry install

# Run tests (integration test requires rights to create, delete and use DynamoDB tables)
make test

# Run linters
make -k lint

# Format code
make format
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