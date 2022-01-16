"""Amazon SQS Batchlib"""

import time
import uuid
from typing import List, Sequence, overload, Tuple, TYPE_CHECKING

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


def create_sqs_client(session: boto3.Session = None) -> "SQSClient":
    """Create default SQS client.

    Args:
        session: boto3 Session to use for creating SQS client. Optional.
                 Default: boto3 default session.
    """
    session = session or boto3.Session()
    region = session.region_name
    return boto3.client("sqs", endpoint_url=f"https://sqs.{region}.amazonaws.com")


def receive_message(
    sqs_client: "SQSClient" = None, session: boto3.Session = None, **kwargs
) -> "ReceiveMessageResultTypeDef":
    """Receive an arbitrary number of messages from an Amazon SQS queue.

    This method performs multiple boto3 SQS receive_message() calls to
    consume an arbitrary number of messages from an Amazon SQS queue. It
    polls the queue for messages until `MaxNumberOfMessages` messages is
    received or `WaitTimeSeconds` has elapsed.

    receive_message() accepts the same arguments and has the same response
    structure as boto3 SQS receive_message() method.

    If you provide a ReceiveRequestAttemptId, receive_message() generates
    a unique ReceiveRequestAttemptId for each SQS request. If you do not
    provide a ReceiveRequestAttemptId, receive_message() sends each SQS
    request without ReceiveRequestAttemptId argument.

    Args:
        sqs_client: boto3 SQS client to use. Optional. Default: client created
                    with default session and configuration.
        session: boto3 Session to use for creating SQS client if sqs_client is
                 not provided. Optional. Default: boto3 default session.
        **kwargs: keyword arguments to pass to boto3 SQS receive_message()
                  method

    Returns:
        SQS messages similar to boto3 SQS receive_message() method.
    """
    sqs_client = sqs_client or create_sqs_client(session)

    batch_size = kwargs.get("MaxNumberOfMessages", 1)
    batching_window = kwargs.get("WaitTimeSeconds", 1)

    batch: List["MessageTypeDef"] = []
    start = time.time()
    while time.time() - start < batching_window and len(batch) < batch_size:
        kwargs["WaitTimeSeconds"] = 1
        kwargs["MaxNumberOfMessages"] = min(batch_size - len(batch), 10)
        if "ReceiveRequestAttemptId" in kwargs:
            kwargs["ReceiveRequestAttemptId"] = str(uuid.uuid4())
        batch.extend(sqs_client.receive_message(**kwargs).get("Messages", []))

    return {"Messages": batch}


def delete_message_batch(
    QueueUrl: str,  # pylint: disable=invalid-name
    Entries: List[
        "DeleteMessageBatchRequestEntryTypeDef"
    ],  # pylint: disable=invalid-name
    sqs_client: "SQSClient" = None,
    session: boto3.Session = None,
) -> "DeleteMessageBatchResultTypeDef":
    """Delete an arbitrary number of messages from an Amazon SQS queue.

    This method performs multiple boto3 SQS delete_message_batch() calls to
    delete an arbitrary number of messages from an Amazon SQS queue.

    delete_message_batch() accepts the same arguments and has the same response
    structure as boto3 SQS delete_message_batch() method.

    Args:
        QueueUrl: The URL of the Amazon SQS queue from which messages are deleted.
        Entries: A list of receipt handles for the messages to be deleted.
        sqs_client: boto3 SQS client to use. Optional. Default: client created
                    with default session and configuration.
        session: boto3 Session to use for creating SQS client if sqs_client is
                 not provided. Optional. Default: boto3 default session.
    Returns:
        Results similar to boto3 SQS delete_message_batch() method.
    """
    sqs_client = sqs_client or create_sqs_client(session)
    result: "DeleteMessageBatchResultTypeDef" = {"Successful": [], "Failed": []}

    while Entries:
        chunk, Entries = Entries[:10], Entries[10:]
        res = sqs_client.delete_message_batch(QueueUrl=QueueUrl, Entries=chunk)

        failed, retryable = _divide_failures(res.get("Failed", []), chunk)
        result["Failed"].extend(failed)
        result["Successful"].extend(res.get("Successful", []))
        Entries = retryable + Entries

    return result


def send_message_batch(
    QueueUrl: str,  # pylint: disable=invalid-name
    Entries: List[  # pylint: disable=invalid-name
        "SendMessageBatchRequestEntryTypeDef"
    ],
    sqs_client: "SQSClient" = None,
    session: boto3.Session = None,
) -> "SendMessageBatchResultTypeDef":
    """Send an arbitrary number of messages to an Amazon SQS queue.

    This method performs multiple boto3 SQS send_message_batch() calls to
    delete an arbitrary number of messages from an Amazon SQS queue.

    send_message_batch() accepts the same arguments and has the same response
    structure as boto3 SQS send_message_batch() method.

    Args:
        QueueUrl: The URL of the Amazon SQS queue to which batched messages
                  are sent.
        Entries: A list of send message entries for the messages to send to
                 SQS.
        sqs_client: boto3 SQS client to use. Optional. Default: client created
                    with default session and configuration.
        session: boto3 Session to use for creating SQS client if sqs_client is
                 not provided. Optional. Default: boto3 default session.

    Returns:
        Results similar to boto3 SQS send_message_batch() method.
    """
    sqs_client = sqs_client or create_sqs_client(session)
    result: "SendMessageBatchResultTypeDef" = {"Successful": [], "Failed": []}

    while Entries:
        chunk, Entries = Entries[:10], Entries[10:]
        res = sqs_client.send_message_batch(QueueUrl=QueueUrl, Entries=chunk)

        failed, retryable = _divide_failures(res.get("Failed", []), chunk)
        result["Failed"].extend(failed)
        result["Successful"].extend(res.get("Successful", []))
        Entries = retryable + Entries

    return result


@overload
def _divide_failures(
    failed: List["BatchResultErrorEntryTypeDef"],
    entries: Sequence["SendMessageBatchRequestEntryTypeDef"],
) -> Tuple[
    List["BatchResultErrorEntryTypeDef"],
    List["SendMessageBatchRequestEntryTypeDef"],
]:
    ...  # pragma: no cover


@overload
def _divide_failures(
    failed: List["BatchResultErrorEntryTypeDef"],
    entries: Sequence["DeleteMessageBatchRequestEntryTypeDef"],
) -> Tuple[
    List["BatchResultErrorEntryTypeDef"],
    List["DeleteMessageBatchRequestEntryTypeDef"],
]:
    ...  # pragma: no cover


def _divide_failures(failed, entries):
    """Helper to divide errors into retryable and non-retryable errors.

    Args;
        failed: list of failed batch operations
        entries: list of entries passed to batch operation

    Returns: tuple with (errors, retryable_entries) where errors contains
        non-retryable batch result entries and retryable_entries contains
        entries that can be retried.
    """
    if not failed:
        return [], []

    not_retryable: List["BatchResultErrorEntryTypeDef"] = []
    retryable: List["SendMessageBatchRequestEntryTypeDef"] = []

    entry_map = {entry["Id"]: entry for entry in entries}
    for msg in failed:
        if msg["SenderFault"]:
            not_retryable.append(msg)
        else:
            retryable.append(entry_map[msg["Id"]])

    return not_retryable, retryable
