# Changelog

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
