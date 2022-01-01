"""Amazon SQS Batchlib"""

import time
from typing import List, Sequence, TYPE_CHECKING

import boto3

if TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_sqs import SQSClient
    from mypy_boto3_sqs.type_defs import (
        MessageTypeDef,
        DeleteMessageBatchRequestEntryTypeDef,
        DeleteMessageBatchResultEntryTypeDef,
        BatchResultErrorEntryTypeDef,
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


def create_sqs_client() -> "SQSClient":
    """Create default SQS client."""
    return boto3.client("sqs")


def consume(
    queue_url: str,
    batch_size: int = 10,
    maximum_batching_window_in_seconds: float = 1,
    sqs_client: "SQSClient" = None,
    **kwargs
) -> "ReceiveMessageResultTypeDef":
    """Consume a batch of messages from SQS.

    This method consumes up-to `batch_size` messages from a queue, making
    multiple ReceiveMessage calls during `maximum_batching_window_in_seconds`
    time window. It polls the queue until `batch_size` messages is received
    or `maximum_batching_window_in_seconds` has elapsed.

    Args:
        queue_url: URL of the SQS Queue to consume.
        batch_size: The maximum number of messages to retrieve in a
            single batch. Default: 10.
        maximum_batching_window_in_seconds: The maximum amount of time
            to gather messages before returning them to the caller, in
            seconds. Default: 1.
        sqs_client: boto3 SQS client to use. Optional. Default:
            client created with default session and configuration.
        **kwargs: Additional arguments to pass to boto3 SQS client
            receive_message() function. Following arguments are not
            supported and will be omitted: QueueUrl, MaxNumberOfMessages,
            WaitTimeSeconds, ReceiveRequestAttemptId

    Returns:
        Dictionary with a single "Messages" item that contains a list of
        SQS messages (same as boto3 SQS client receive_message()).

    """
    sqs_client = sqs_client or create_sqs_client()

    # Pop unsupported args and args we define ourselves which cannot be
    # overwritten by the user.
    kwargs.pop("QueueUrl", None)
    kwargs.pop("MaxNumberOfMessages", None)
    kwargs.pop("WaitTimeSeconds", None)
    kwargs.pop("ReceiveRequestAttemptId", None)

    batch: List["MessageTypeDef"] = []
    start = time.time()
    while (
        time.time() - start < maximum_batching_window_in_seconds
        and len(batch) < batch_size
    ):
        batch.extend(
            sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(batch_size - len(batch), 10),
                WaitTimeSeconds=1,
                **kwargs
            ).get("Messages", [])
        )

    return {"Messages": batch}


def delete_message_batch(
    QueueUrl: str,  # pylint: disable=invalid-name
    Entries: Sequence[
        "DeleteMessageBatchRequestEntryTypeDef"
    ],  # pylint: disable=invalid-name
    sqs_client: "SQSClient" = None,
) -> "DeleteMessageBatchResultTypeDef":
    """Delete arbitrary number of messages from SQS queue.

    This method performs multiple boto3 SQS delete_message_batch() to delete an
    arbitrary number of messages from an SQS queue.

    Args:
        QueueUrl: The URL of the Amazon SQS queue from which messages are deleted.
        Entries: A list of receipt handles for the messages to be deleted.
        sqs_client: boto3 SQS client to use. Optional. Default: client created with default
                    session and configuration.

    Returns:
        Same as boto3 SQS delete_message_batch() method.
    """
    sqs_client = sqs_client or create_sqs_client()
    result: "DeleteMessageBatchResultTypeDef" = {"Successful": [], "Failed": []}

    while Entries:
        chunk, Entries = Entries[:10], Entries[10:]
        res = sqs_client.delete_message_batch(QueueUrl=QueueUrl, Entries=chunk)

        result["Failed"].extend(res.get("Failed", []))
        result["Successful"].extend(res.get("Successful", []))

    return result
