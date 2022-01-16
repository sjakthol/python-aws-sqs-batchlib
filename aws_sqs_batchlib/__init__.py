"""Amazon SQS Batchlib"""
__version__ = "2.0.0"

from .aws_sqs_batchlib import (
    create_sqs_client,
    delete_message_batch,
    receive_message,
    send_message_batch,
)
