# pylint: disable=missing-module-docstring,missing-function-docstring,redefined-outer-name
import itertools
import operator

import botocore.session
from moto import mock_sqs
import pytest

import aws_sqs_batchlib

TEST_QUEUE_NAME = "aws-sqs-batchlib-testqueue"


@pytest.fixture()
def _setup_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-north-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture()
def mock_queue(_setup_env):
    with mock_sqs():
        sqs = botocore.session.get_session().create_client("sqs")
        res = sqs.create_queue(QueueName=TEST_QUEUE_NAME)
        queue_url = res.get("QueueUrl")

        yield queue_url

        sqs.delete_queue(QueueUrl=queue_url)


def test_aws_sqs_batchlib(mock_queue):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(100):
        sqs.send_message(QueueUrl=mock_queue, MessageBody=str(i))

    batch = aws_sqs_batchlib.consume(mock_queue, 50)
    assert len(batch["Messages"]) == 50

    batch2 = aws_sqs_batchlib.consume(mock_queue, 100)
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
