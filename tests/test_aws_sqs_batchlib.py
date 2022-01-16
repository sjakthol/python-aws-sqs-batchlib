# pylint: disable=missing-module-docstring,missing-function-docstring,redefined-outer-name
import contextlib
import unittest.mock
import uuid

import boto3
import botocore.exceptions
from moto import mock_sqs
import pytest
from urllib3.exceptions import ProtocolError

import aws_sqs_batchlib

TEST_QUEUE_NAME_PREFIX = "aws-sqs-batchlib-testqueue"
SKIP_INTEGRATION_TESTS = False

QUEUE_MOCKED = "mocked queue"
QUEUE_REAL = "real queue"


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-north-1")


def _fake_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


def create_test_queue(fifo=False):
    sqs = aws_sqs_batchlib.create_sqs_client()
    try:
        if fifo:
            res = sqs.create_queue(
                QueueName=f"{TEST_QUEUE_NAME_PREFIX}-{uuid.uuid4()}.fifo",
                Attributes={"FifoQueue": "true"},
            )
        else:
            res = sqs.create_queue(QueueName=f"{TEST_QUEUE_NAME_PREFIX}-{uuid.uuid4()}")
    except (
        botocore.exceptions.BotoCoreError,
        botocore.exceptions.ClientError,
    ) as exc:
        global SKIP_INTEGRATION_TESTS  # pylint: disable=global-statement
        SKIP_INTEGRATION_TESTS = True
        pytest.skip(
            f"Failed to create sqs queue for testing, skipping integration test ({exc})"
        )
        return None

    return res.get("QueueUrl")


@pytest.fixture(params=[QUEUE_MOCKED, QUEUE_REAL])
def sqs_queue(request, monkeypatch, _setup_env):
    mocked = request.param == QUEUE_MOCKED
    if mocked:
        _fake_credentials(monkeypatch)
    elif SKIP_INTEGRATION_TESTS:
        pytest.skip("Unable to create real queues, skipping integration test")
        return

    sqs_mock_or_null = mock_sqs if mocked else contextlib.suppress
    with sqs_mock_or_null():
        queue_url = create_test_queue()
        yield queue_url
        sqs = boto3.client("sqs")
        sqs.delete_queue(QueueUrl=queue_url)


@pytest.fixture(params=[QUEUE_MOCKED, QUEUE_REAL])
def fifo_queue(request, monkeypatch, _setup_env):
    mocked = request.param == QUEUE_MOCKED
    if mocked:
        _fake_credentials(monkeypatch)
    elif SKIP_INTEGRATION_TESTS:
        pytest.skip("Unable to create real queues, skipping integration test")
        return

    sqs_mock_or_null = mock_sqs if mocked else contextlib.suppress
    with sqs_mock_or_null():
        queue_url = create_test_queue(fifo=True)
        yield queue_url
        sqs = boto3.client("sqs")
        sqs.delete_queue(QueueUrl=queue_url)


def read_messages(queue_url, num_messages, delete=True):
    """Helper to read and delete N messages from SQS queue."""
    sqsc = aws_sqs_batchlib.create_sqs_client()
    messages = []
    while len(messages) < num_messages:
        # Read some messages
        msgs = sqsc.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
        ).get("Messages", [])

        messages.extend(msgs)

        if delete:
            sqsc.delete_message_batch(
                QueueUrl=queue_url,
                Entries=[
                    {"Id": msg["MessageId"], "ReceiptHandle": msg["ReceiptHandle"]}
                    for msg in msgs
                ],
            )

    return messages


@pytest.mark.parametrize(
    ["num_messages", "wait_time"], [(0, 1), (5, 5), (10, 10), (11, 11), (48, 15)]
)
def test_receive(sqs_queue, num_messages, wait_time):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(num_messages):
        sqs.send_message(QueueUrl=sqs_queue, MessageBody=str(i))

    batch = aws_sqs_batchlib.receive_message(
        QueueUrl=sqs_queue, MaxNumberOfMessages=num_messages, WaitTimeSeconds=wait_time
    )
    messages = batch["Messages"]
    assert len(messages) == num_messages


def test_receive_no_batching_args(sqs_queue):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(4):
        sqs.send_message(QueueUrl=sqs_queue, MessageBody=str(i))

    aws_sqs_batchlib.receive_message(QueueUrl=sqs_queue)


def test_receive_leave_extra_messages(sqs_queue):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(25):
        sqs.send_message(QueueUrl=sqs_queue, MessageBody=str(i))

    batch = aws_sqs_batchlib.receive_message(
        QueueUrl=sqs_queue, MaxNumberOfMessages=18, WaitTimeSeconds=15
    )
    messages = batch["Messages"]
    assert len(messages) == 18


def test_receive_custom_session(sqs_queue):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(4):
        sqs.send_message(QueueUrl=sqs_queue, MessageBody=str(i))

    aws_sqs_batchlib.receive_message(
        QueueUrl=sqs_queue, session=boto3.Session(region_name="eu-north-1")
    )


def test_receive_custom_session_and_client(sqs_queue):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(4):
        sqs.send_message(QueueUrl=sqs_queue, MessageBody=str(i))

    aws_sqs_batchlib.receive_message(
        QueueUrl=sqs_queue,
        session=boto3.Session(region_name="eu-west-1"),
        sqs_client=sqs,
    )


@pytest.mark.parametrize("fifo_queue", [QUEUE_REAL], indirect=True)
@pytest.mark.parametrize(["num_messages", "num_received"], [(0, 0), (5, 5), (11, 10)])
def test_receive_fifo_one_message_groups(fifo_queue, num_messages, num_received):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(num_messages):
        sqs.send_message(
            QueueUrl=fifo_queue,
            MessageBody=f"1-{i}",
            MessageDeduplicationId=f"1-{i}",
            MessageGroupId="1",
        )

    batch = aws_sqs_batchlib.receive_message(
        QueueUrl=fifo_queue,
        MaxNumberOfMessages=num_messages,
        WaitTimeSeconds=1,
    )

    assert len(batch["Messages"]) == num_received


@pytest.mark.parametrize("fifo_queue", [QUEUE_REAL], indirect=True)
@pytest.mark.parametrize(["num_messages", "num_received"], [(0, 0), (5, 10), (11, 20)])
def test_receive_fifo_multiple_message_groups(fifo_queue, num_messages, num_received):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for j in range(2):
        for i in range(num_messages):
            sqs.send_message(
                QueueUrl=fifo_queue,
                MessageBody=f"{j}-{i}",
                MessageDeduplicationId=f"{j}-{i}",
                MessageGroupId=f"{j}",
            )

    batch = aws_sqs_batchlib.receive_message(
        QueueUrl=fifo_queue,
        MaxNumberOfMessages=num_messages * 2,
        WaitTimeSeconds=1,
    )

    assert len(batch["Messages"]) == num_received

    if num_received:
        included_groups = {msg["Body"].split("-")[0] for msg in batch["Messages"]}
        assert included_groups == {"0", "1"}, "got messages from two message groups"


@pytest.mark.parametrize("fifo_queue", [QUEUE_REAL], ids=["real queue"], indirect=True)
def test_receive_fifo_retry_with_attempt_id(fifo_queue):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(2):
        sqs.send_message(
            QueueUrl=fifo_queue,
            MessageBody=f"{i}",
            MessageDeduplicationId=f"{i}",
            MessageGroupId="0",
        )

    with unittest.mock.patch(
        "botocore.awsrequest.AWSResponse",
        side_effect=[ProtocolError()] + [unittest.mock.DEFAULT] * 100,
        wraps=botocore.awsrequest.AWSResponse,
    ):
        batch = aws_sqs_batchlib.receive_message(
            QueueUrl=fifo_queue,
            ReceiveRequestAttemptId="attempt-1",
            MaxNumberOfMessages=15,
            WaitTimeSeconds=2,
            VisibilityTimeout=30,
            sqs_client=sqs,
        )

    # Two messages received as the retry after first failure had the same
    # ReceiveRequestAttemptId (response to first request was replayed by
    # SQS)
    assert len(batch["Messages"]) == 2


@pytest.mark.parametrize("fifo_queue", [QUEUE_REAL], ids=["real queue"], indirect=True)
def test_receive_fifo_retry_without_attempt_id(fifo_queue):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(2):
        sqs.send_message(
            QueueUrl=fifo_queue,
            MessageBody=f"{i}",
            MessageDeduplicationId=f"{i}",
            MessageGroupId="0",
        )

    with unittest.mock.patch(
        "botocore.awsrequest.AWSResponse",
        side_effect=[ProtocolError()] + [unittest.mock.DEFAULT] * 100,
        wraps=botocore.awsrequest.AWSResponse,
    ):
        batch = aws_sqs_batchlib.receive_message(
            QueueUrl=fifo_queue,
            MaxNumberOfMessages=15,
            WaitTimeSeconds=2,
            VisibilityTimeout=30,
            sqs_client=sqs,
        )

    # No messages received as the retry after first failure had different
    # ReceiveRequestAttemptId (response to first request was not replayed
    # by SQS)
    assert not batch["Messages"]


@pytest.mark.parametrize(["num_messages"], [(0,), (5,), (10,), (11,)])
def test_delete(sqs_queue, num_messages):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(num_messages):
        sqs.send_message(QueueUrl=sqs_queue, MessageBody=str(i))

    messages = read_messages(sqs_queue, num_messages, delete=False)
    assert len(messages) == num_messages

    delete_requests = [
        {"Id": msg["MessageId"], "ReceiptHandle": msg["ReceiptHandle"]}
        for msg in messages
    ]
    resp = aws_sqs_batchlib.delete_message_batch(
        QueueUrl=sqs_queue, Entries=delete_requests
    )

    assert not resp["Failed"]
    assert len(resp["Successful"]) == num_messages


def test_delete_custom_session(sqs_queue):
    num_messages = 10
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(num_messages):
        sqs.send_message(QueueUrl=sqs_queue, MessageBody=str(i))

    messages = read_messages(sqs_queue, num_messages, delete=False)

    delete_requests = [
        {"Id": msg["MessageId"], "ReceiptHandle": msg["ReceiptHandle"]}
        for msg in messages
    ]
    resp = aws_sqs_batchlib.delete_message_batch(
        QueueUrl=sqs_queue,
        Entries=delete_requests,
        session=boto3.Session(region_name="eu-north-1"),
    )

    assert not resp["Failed"]
    assert len(resp["Successful"]) == num_messages


def test_delete_custom_session_and_client(sqs_queue):
    num_messages = 10
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(num_messages):
        sqs.send_message(QueueUrl=sqs_queue, MessageBody=str(i))

    messages = read_messages(sqs_queue, num_messages, delete=False)

    delete_requests = [
        {"Id": msg["MessageId"], "ReceiptHandle": msg["ReceiptHandle"]}
        for msg in messages
    ]
    resp = aws_sqs_batchlib.delete_message_batch(
        QueueUrl=sqs_queue,
        Entries=delete_requests,
        session=boto3.Session(region_name="eu-west-1"),  # wrong region
        sqs_client=sqs,
    )

    assert not resp["Failed"]
    assert len(resp["Successful"]) == num_messages


def test_delete_client_retry_failures():
    client_mock = unittest.mock.Mock(spec=boto3.client("sqs"))
    client_mock.delete_message_batch.side_effect = [
        {
            "Successful": [{"Id": f"{i}"} for i in range(2, 10)],
            "Failed": [
                {
                    "Id": "0",
                    "SenderFault": True,
                    "Code": "ReceiptHandleIsInvalid",
                    "Message": "ReceiptHandleIsInvalid",
                },
                {
                    "Id": "1",
                    "SenderFault": False,
                    "Code": "InternalFailure",
                    "Message": "InternalFailure",
                },
            ],
        },
        {"Successful": [{"Id": "1"}, {"Id": "10"}]},
    ]

    delete_requests = [{"Id": f"{i}", "ReceiptHandle": f"{i}"} for i in range(0, 11)]

    resp = aws_sqs_batchlib.delete_message_batch(
        QueueUrl=sqs_queue, Entries=delete_requests, sqs_client=client_mock
    )

    assert resp == {
        "Successful": [
            {"Id": "2"},
            {"Id": "3"},
            {"Id": "4"},
            {"Id": "5"},
            {"Id": "6"},
            {"Id": "7"},
            {"Id": "8"},
            {"Id": "9"},
            {"Id": "1"},
            {"Id": "10"},
        ],
        "Failed": [
            {
                "Id": "0",
                "SenderFault": True,
                "Code": "ReceiptHandleIsInvalid",
                "Message": "ReceiptHandleIsInvalid",
            }
        ],
    }


@pytest.mark.parametrize(["num_messages"], [(0,), (5,), (10,)])
def test_delete_fifo_one_message_group(fifo_queue, num_messages):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for i in range(num_messages):
        sqs.send_message(
            QueueUrl=fifo_queue,
            MessageBody=f"1-{i}",
            MessageDeduplicationId=f"1-{i}",
            MessageGroupId="1",
        )

    batch = aws_sqs_batchlib.receive_message(
        QueueUrl=fifo_queue,
        MaxNumberOfMessages=num_messages,
        WaitTimeSeconds=1,
    )

    assert len(batch["Messages"]) == num_messages

    resp = aws_sqs_batchlib.delete_message_batch(
        QueueUrl=fifo_queue,
        Entries=[
            {"Id": msg["MessageId"], "ReceiptHandle": msg["ReceiptHandle"]}
            for msg in batch["Messages"]
        ],
    )

    assert not resp["Failed"]
    assert len(resp["Successful"]) == num_messages


@pytest.mark.parametrize(["num_messages"], [(5,), (10,)])
def test_delete_fifo_multiple_message_groups(fifo_queue, num_messages):
    sqs = aws_sqs_batchlib.create_sqs_client()
    for j in range(2):
        for i in range(num_messages):
            sqs.send_message(
                QueueUrl=fifo_queue,
                MessageBody=f"{j}-{i}",
                MessageDeduplicationId=f"{j}-{i}",
                MessageGroupId=f"{j}",
            )

    batch = aws_sqs_batchlib.receive_message(
        QueueUrl=fifo_queue,
        MaxNumberOfMessages=num_messages * 2,
        WaitTimeSeconds=1,
    )

    assert len(batch["Messages"]) == num_messages * 2

    resp = aws_sqs_batchlib.delete_message_batch(
        QueueUrl=fifo_queue,
        Entries=[
            {"Id": msg["MessageId"], "ReceiptHandle": msg["ReceiptHandle"]}
            for msg in batch["Messages"]
        ],
    )

    assert not resp["Failed"]
    assert len(resp["Successful"]) == num_messages * 2


@pytest.mark.parametrize(["num_messages"], [(0,), (5,), (10,), (11,)])
def test_send(sqs_queue, num_messages):
    resp = aws_sqs_batchlib.send_message_batch(
        QueueUrl=sqs_queue,
        Entries=[{"Id": f"{i}", "MessageBody": f"{i}"} for i in range(num_messages)],
    )

    assert not resp["Failed"]
    assert len(resp["Successful"]) == num_messages

    messages = read_messages(sqs_queue, num_messages, delete=False)
    assert len(messages) == num_messages


def test_send_custom_session(sqs_queue):
    num_messages = 10
    resp = aws_sqs_batchlib.send_message_batch(
        QueueUrl=sqs_queue,
        Entries=[{"Id": f"{i}", "MessageBody": f"{i}"} for i in range(num_messages)],
        session=boto3.Session(region_name="eu-north-1"),
    )

    assert not resp["Failed"]
    assert len(resp["Successful"]) == num_messages


def test_send_custom_session_and_client(sqs_queue):
    num_messages = 10
    resp = aws_sqs_batchlib.send_message_batch(
        QueueUrl=sqs_queue,
        Entries=[{"Id": f"{i}", "MessageBody": f"{i}"} for i in range(num_messages)],
        session=boto3.Session(
            region_name="eu-west-1"
        ),  # session has wrong region, client is used
        sqs_client=aws_sqs_batchlib.create_sqs_client(),
    )

    assert not resp["Failed"]
    assert len(resp["Successful"]) == num_messages


@pytest.mark.parametrize(["num_messages"], [(24,)])
def test_send_fifo_retains_order(fifo_queue, num_messages):
    resp = aws_sqs_batchlib.send_message_batch(
        QueueUrl=fifo_queue,
        Entries=[
            {
                "Id": f"{i}",
                "MessageBody": f"{i}",
                "MessageGroupId": "0",
                "MessageDeduplicationId": f"{i}",
            }
            for i in range(num_messages)
        ],
    )

    assert not resp["Failed"]
    assert len(resp["Successful"]) == num_messages

    messages = read_messages(fifo_queue, num_messages, delete=True)
    assert [msg["Body"] for msg in messages] == [str(i) for i in range(num_messages)]


def test_send_retry_failures():
    client_mock = unittest.mock.Mock(spec=boto3.client("sqs"))
    client_mock.send_message_batch.side_effect = [
        {
            "Successful": [{"Id": f"{i}"} for i in range(2, 10)],
            "Failed": [
                {
                    "Id": "0",
                    "SenderFault": True,
                    "Code": "InvalidMessageContents",
                    "Message": "InvalidMessageContents",
                },
                {
                    "Id": "1",
                    "SenderFault": False,
                    "Code": "InternalFailure",
                    "Message": "InternalFailure",
                },
            ],
        },
        {"Successful": [{"Id": "1"}, {"Id": "10"}]},
    ]

    delete_requests = [{"Id": f"{i}", "MessageBody": f"{i}"} for i in range(0, 11)]

    resp = aws_sqs_batchlib.send_message_batch(
        QueueUrl=sqs_queue, Entries=delete_requests, sqs_client=client_mock
    )

    assert resp == {
        "Successful": [
            {"Id": "2"},
            {"Id": "3"},
            {"Id": "4"},
            {"Id": "5"},
            {"Id": "6"},
            {"Id": "7"},
            {"Id": "8"},
            {"Id": "9"},
            {"Id": "1"},
            {"Id": "10"},
        ],
        "Failed": [
            {
                "Id": "0",
                "SenderFault": True,
                "Code": "InvalidMessageContents",
                "Message": "InvalidMessageContents",
            }
        ],
    }
