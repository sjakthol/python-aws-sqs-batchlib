# Changelog

## 3.0.0 - 2024-01-31

### Changed

* **Breaking:** Drop Python 3.7 support. Minimum supported Python version is Python 3.8

**All Changes**: https://github.com/sjakthol/python-aws-sqs-batchlib/compare/v2.0.0...v3.0.0

## 2.0.0 - 2022-01-16

### Changed

* **Breaking:** Replace the `consume()` method with a `receive_message()` method. Update your code from
   ```python
   batch = aws_sqs_batchlib.consume(
       queue_url, batch_size=100, maximum_batching_window_in_seconds=15
   )
   ```

   to

   ```python
   batch = aws_sqs_batchlib.receive_message(
       QueueUrl=queue_url, MaxNumberOfMessages=100, WaitTimeSeconds=15
   )
   ```
* Use modern Amazon SQS service endpoints by default to support VPC endpoints.

### Added

* `delete_message_batch()`: Add `session` argument for providing a custom boto3 Sessions for the library.
* `delete_message_batch()`: Add support for FIFO queues.
* `delete_message_batch()`: Automatically retry failed delete operations if the failure is retryable.
* `receive_message()`: Add new `receive_message()` method to receive an arbitrary number of messages from Amazon SQS.
* `receive_message()`: Add `session` argument for providing a custom boto3 Sessions for the library.
* `receive_message()`: Add support for FIFO queues.
* `send_message_batch()`: Add new `send_message_batch()` method to send an arbitrary number of messages to Amazon SQS.
* `send_message_batch()`: Add `session` argument for providing a custom boto3 Sessions for the library.
* `send_message_batch()`: Add support for FIFO queues.
* `send_message_batch()`: Automatically retry failed send operations if the failure is retryable.

### Fixed

* `receive_message()`: Generate unique `ReceiveRequestAttemptId` parameter for each distinct `ReceiveMessage` API call
  if `ReceiveRequestAttemptId` is provided to `receive_message()`.

**All Changes**: https://github.com/sjakthol/python-aws-sqs-batchlib/compare/v1.1.0...v2.0.0

## 1.2.0 - 2022-01-01

### Added

* Add `delete_message_batch()` method to delete an arbitrary number of messages from an Amazon SQS queue

### Fixed

* Prevent `receive_message()` from consuming more than requested amount of messages from an Amazon SQS queue

**All Changes**: https://github.com/sjakthol/python-aws-sqs-batchlib/compare/v1.1.0...v1.2.0

## 1.1.0 - 2022-01-01

### Changed

* Migrate from botocore to boto3

### Fixed

* Change package structure to fix type checking support

**All Changes**: https://github.com/sjakthol/python-aws-sqs-batchlib/compare/v1.0.1...v1.1.0

## 1.0.1 - 2022-01-01

### Fixed

* Fix value of `__version__` in `aws_sqs_batchlib` module

**All Changes**: https://github.com/sjakthol/python-aws-sqs-batchlib/compare/v1.0.0...v1.0.1

## 1.0.0 - 2022-01-01

### Changed

* **BREAKING:** Drop support for Python 3.6

**All Changes**: https://github.com/sjakthol/python-aws-sqs-batchlib/compare/v0.1.2...v1.0.0
