"""Amazon SQS Batchlib"""

import time
from typing import List, Sequence, TYPE_CHECKING

import boto3

if TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_sqs import SQSClient
    from mypy_boto3_sqs.type_defs import (
        BatchResultErrorEntryTypeDef,
        DeleteMessageBatchRequestEntryTypeDef,
        DeleteMessageBatchResultEntryTypeDef,
        MessageTypeDef,
        SendMessageBatchRequestEntryTypeDef,
        SendMessageBatchResultEntryTypeDef,
    )
    from typing_extensions import TypedDict

    ReceiveMessageResultTypeDef = TypedDict(
        "ReceiveMessageResultTypeDef",
        {"Messages": List["MessageTypeDef"]},
    )

    DeleteMessageBatchResultTypeDef = TypedDict(
        "DeleteMessageBatchResultTypeDef",
        {
            "Successful": List["DeleteMessageBatchResultEntryTypeDef"],
            "Failed": List["BatchResultErrorEntryTypeDef"],
        },
    )

    SendMessageBatchResultTypeDef = TypedDict(
        "SendMessageBatchResultTypeDef",
        {
            "Successful": List["SendMessageBatchResultEntryTypeDef"],
            "Failed": List["BatchResultErrorEntryTypeDef"],
        },
    )


def create_sqs_client() -> "SQSClient":
    """Create default SQS client."""
    return boto3.client("sqs")


def receive_message(
    sqs_client: "SQSClient" = None, **kwargs
) -> "ReceiveMessageResultTypeDef":
    """Receive arbitrary number of messages from an Amazon SQS queue.

    This method performs multiple boto3 SQS receive_message() calls to
    consume an arbitrary number of messages from an SQS queue. It polls
    the queue until `MaxNumberOfMessages` messages is received or
    `WaitTimeSeconds` has elapsed.

    It accepts the same arguments as boto3 SQS receive_message().

    Args:
        sqs_client: boto3 SQS client to use. Optional. Default:
                    client created with default session and configuration.
        **kwargs: keyword arguments to pass to boto3 SQS receive_message()
                  method
    """
    sqs_client = sqs_client or create_sqs_client()

    batch_size = kwargs.get("MaxNumberOfMessages", 1)
    batching_window = kwargs.get("WaitTimeSeconds", 1)

    batch: List["MessageTypeDef"] = []
    start = time.time()
    while time.time() - start < batching_window and len(batch) < batch_size:
        kwargs["WaitTimeSeconds"] = 1
        kwargs["MaxNumberOfMessages"] = min(batch_size - len(batch), 10)
        batch.extend(sqs_client.receive_message(**kwargs).get("Messages", []))

    return {"Messages": batch}


def delete_message_batch(
    QueueUrl: str,  # pylint: disable=invalid-name
    Entries: Sequence[
        "DeleteMessageBatchRequestEntryTypeDef"
    ],  # pylint: disable=invalid-name
    sqs_client: "SQSClient" = None,
) -> "DeleteMessageBatchResultTypeDef":
    """Delete arbitrary number of messages from an Amazon SQS queue.

    This method performs multiple boto3 SQS delete_message_batch() calls to
    delete an arbitrary number of messages from an Amazon SQS queue.

    It accepts the same arguments as boto3 SQS delete_message_batch().

    Args:
        QueueUrl: The URL of the Amazon SQS queue from which messages are deleted.
        Entries: A list of receipt handles for the messages to be deleted.
        sqs_client: boto3 SQS client to use. Optional. Default: client created with default
                    session and configuration.

    Returns:
        A dict of form { "Successful": [], "Failed" [] } with structure similar to boto3 SQS
        delete_message_batch() method return value.
    """
    sqs_client = sqs_client or create_sqs_client()
    result: "DeleteMessageBatchResultTypeDef" = {"Successful": [], "Failed": []}

    while Entries:
        chunk, Entries = Entries[:10], Entries[10:]
        res = sqs_client.delete_message_batch(QueueUrl=QueueUrl, Entries=chunk)

        result["Failed"].extend(res.get("Failed", []))
        result["Successful"].extend(res.get("Successful", []))

    return result


def send_message_batch(
    QueueUrl: str,  # pylint: disable=invalid-name
    Entries: Sequence[  # pylint: disable=invalid-name
        "SendMessageBatchRequestEntryTypeDef"
    ],
    sqs_client: "SQSClient" = None,
) -> "SendMessageBatchResultTypeDef":
    """Send arbitrary number of messages to an Amazon SQS queue.

    This method performs multiple boto3 SQS send_message_batch() calls to
    send an arbitrary number of messages to an Amazon SQS queue.

    It accepts the same arguments as boto3 SQS send_message_batch().

    Args:
        QueueUrl: The URL of the Amazon SQS queue to which batched messages are sent.
        Entries: A list of `` SendMessageBatchRequestEntry `` items.
        sqs_client: boto3 SQS client to use. Optional. Default: client created with default
                    session and configuration.

    Returns:
        A dict of form { "Successful": [], "Failed" [] } with structure similar to boto3 SQS
        send_message_batch() method return value.
    """
    sqs_client = sqs_client or create_sqs_client()
    result: "SendMessageBatchResultTypeDef" = {"Successful": [], "Failed": []}

    while Entries:
        chunk, Entries = Entries[:10], Entries[10:]
        res = sqs_client.send_message_batch(QueueUrl=QueueUrl, Entries=chunk)

        result["Failed"].extend(res.get("Failed", []))
        result["Successful"].extend(res.get("Successful", []))

    return result
