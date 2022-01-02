# aws-sqs-batchlib for Python

Consume and process Amazon SQS queues in large batches.

## Features

* Consume arbitrary number of messages from an Amazon SQS queue.

  * Define maximum batch size and batching window in seconds to receive a batch
    of messages from Amazon SQS queue similar to Lambda Event Source Mapping.

* Send arbitrary number of messages to an Amazon SQS queue.

* Delete arbitrary number of messages from an Amazon SQS queue.


## Installation

Install from PyPI with pip

```
pip install aws-sqs-batchlib
```

or with the package manager of choice.

## Usage

`aws-sqs-batchlib` provides the following methods:

* `delete_message_batch()` - Delete arbitrary number of messages from an Amazon SQS queue.
* `receive_message()` - Receive arbitrary number of messages from an Amazon SQS queue.
* `send_message_batch()` - Send arbitrary number of messages to an Amazon SQS queue.

These methods invoke the corresponding boto3 [SQS.Client](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#client)
methods multiple times to send, receive or delete an arbitrary number of messages from an Amazon SQS queue. They accept the same arguments and have
the same response structure as their boto3 counterparts. See boto3 documentation for more details:

* [delete_message_batch()](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Client.delete_message_batch)
* [receive_message()](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Client.receive_message)
* [send_message_batch()](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Client.send_message_batch)

### Receive

```python
import aws_sqs_batchlib

# Receive up-to 100 messages from the given queue, polling the queue for
# up-to 15 seconds to fill the batch.
res = aws_sqs_batchlib.receive_message(
    QueueUrl = "https://sqs.eu-north-1.amazonaws.com/123456789012/MyQueue",
    MaxNumberOfMessages=100,
    WaitTimeSeconds=15,
)

# Returns messages in the same format as boto3 / botocore SQS Client
# receive_message() method.
assert res == {
    'Messages': [
        {'MessageId': '[.]', 'ReceiptHandle': 'AQ[.]JA==', 'MD5OfBody': '[.]', 'Body': '[.]'},
        {'MessageId': '[.]', 'ReceiptHandle': 'AQ[.]wA==', 'MD5OfBody': '[.]', 'Body': '[.]'}
        # ... up-to 100 messages
    ]
}
```

### Send

```python
import aws_sqs_batchlib

# Send an arbitrary number of messages to a queue
res = aws_sqs_batchlib.send_message_batch(
    QueueUrl="https://sqs.eu-north-1.amazonaws.com/123456789012/MyQueue",
    Entries=[
        {"Id": "1", "MessageBody": "<...>"},
        {"Id": "2", "MessageBody": "<...>", "DelaySeconds": 1000000},
        # ...
        {"Id": "175", "MessageBody": "<...>"},
        # ...
    ],
)

# Returns result in the same format as boto3 / botocore SQS Client
# send_message_batch() method.
assert res == {
    "Successful": [
        {"Id": "1", "MessageId": "<...>", "MD5OfMessageBody": "<...>"},
        # ...
    ],
    "Failed": [
        {
            "Id": "2",
            "SenderFault": True,
            "Code": "InvalidParameterValue",
            "Message": "Value 1000000 for parameter DelaySeconds is invalid. Reason: DelaySeconds must be >= 0 and <= 900.",
        }
    ],
}
```

### Delete

```python
import aws_sqs_batchlib

# Delete an arbitrary number of messages from a queue
res = aws_sqs_batchlib.delete_message_batch(
    QueueUrl="https://sqs.eu-north-1.amazonaws.com/123456789012/MyQueue",
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

Use `benchmark/end2end.py` to benchmark and test the library functionality and performance. Execute following commands in Poetry virtualenv (execute `poetry shell` to get there):

```bash
# Setup
export PYTHONPATH=$(pwd)
export AWS_DEFAULT_REGION=eu-north-1

# Send, receive and delete 512 messages, run test 5 times
python3 benchmark/end2end.py \
  --queue-url https://sqs.eu-north-1.amazonaws.com/123456789012/MyQueue --num-messages 512 --iterations 5
```

Benchmarks against an Amazon SQS queue on the same AWS region (eu-north-1, c5.large instance) show following
throughput:

* Send - ~500 to ~800 messages / second
* Receive - ~800 to ~1400 messages / second
* Delete - ~900 to ~1600 messages / second

## License

MIT.