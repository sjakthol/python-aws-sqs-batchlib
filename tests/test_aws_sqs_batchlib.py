# pylint: disable=missing-module-docstring,missing-function-docstring,redefined-outer-name
import contextlib
import itertools
import operator
import uuid

import boto3
import botocore.exceptions
from moto import mock_sqs
import pytest

import aws_sqs_batchlib

TEST_QUEUE_NAME_PREFIX = "aws-sqs-batchlib-testqueue"


@pytest.fixture()
def _setup_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-north-1")


def _fake_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture(params=[True, False], ids=("mocked queue", "real queue"))
def sqs_queue(request, monkeypatch, _setup_env):
    mocked = request.param
    if mocked:
        _fake_credentials(monkeypatch)

    sqs_mock_or_null = mock_sqs if mocked else contextlib.suppress
    with sqs_mock_or_null():
        sqs = boto3.client("sqs")
        try:
            res = sqs.create_queue(QueueName=f"{TEST_QUEUE_NAME_PREFIX}-{uuid.uuid4()}")
        except (
            botocore.exceptions.BotoCoreError,
            botocore.exceptions.ClientError,
        ) as exc:
            pytest.skip(
                f"Failed to create sqs queue for testing, skipping integration test ({exc})"
            )
            return

        queue_url = res.get("QueueUrl")

        yield queue_url

        sqs.delete_queue(QueueUrl=queue_url)


def test_consume(sqs_queue):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(100):
        sqs.send_message(QueueUrl=sqs_queue, MessageBody=str(i))

    batch = aws_sqs_batchlib.consume(sqs_queue, 50)
    assert len(batch["Messages"]) == 50

    batch2 = aws_sqs_batchlib.consume(sqs_queue, 100)
    assert len(batch2["Messages"]) == 50

    assert (
        sorted(
            map(
                operator.itemgetter("Body"),
                itertools.chain(batch["Messages"], batch2["Messages"]),
            )
        )
        == sorted([str(i) for i in range(100)])
    )
