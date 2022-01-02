"""End-to-end test / benchmark for aws-sqs-batchlib library."""

import argparse
import contextlib
import json
import logging
import time

import aws_sqs_batchlib
import boto3


@contextlib.contextmanager
def stopwatch():
    """Measure runtime of a block of code.

    >>> with stopwatch() as get_elapsed_time:
    ...     pass
    >>> runtime = get_elapsed_time()
    """
    start = time.perf_counter()
    yield lambda: time.perf_counter() - start


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--queue-url",
        type=str,
        help="Queue to operate on",
        required=True,
    )
    parser.add_argument(
        "-n",
        "--num-messages",
        type=int,
        help="Number of messages to operate on per iteration.",
        default=100,
    )
    parser.add_argument(
        "-i",
        "--iterations",
        type=int,
        help="Number of iterations to perform",
        default=1,
    )

    return parser.parse_args()


def run_iteration(args, i, sqsc):
    with stopwatch() as get_elapsed_time:
        resp = aws_sqs_batchlib.send_message_batch(
            sqs_client=sqsc,
            QueueUrl=args.queue_url,
            Entries=[
                {"Id": f"{i}", "MessageBody": "a" * 1024}
                for i in range(args.num_messages)
            ],
        )
    send_time = get_elapsed_time()
    send_per_second = len(resp["Successful"]) / send_time
    logging.info(
        "[Run=%i] Sent %i messages in %03f seconds (%i / second; %i failed)",
        i,
        len(resp["Successful"]),
        send_time,
        send_per_second,
        len(resp["Failed"]),
    )

    with stopwatch() as get_elapsed_time:
        resp = aws_sqs_batchlib.receive_message(
            sqs_client=sqsc,
            QueueUrl=args.queue_url,
            MaxNumberOfMessages=args.num_messages,
            WaitTimeSeconds=30,
        )
    receive_time = get_elapsed_time()
    receive_per_second = len(resp["Messages"]) / receive_time
    logging.info(
        "[Run=%i] Received %i messages in %03f seconds (%i / second)",
        i,
        len(resp["Messages"]),
        receive_time,
        receive_per_second,
    )

    with stopwatch() as get_elapsed_time:
        resp = aws_sqs_batchlib.delete_message_batch(
            sqs_client=sqsc,
            QueueUrl=args.queue_url,
            Entries=[
                {"Id": msg["MessageId"], "ReceiptHandle": msg["ReceiptHandle"]}
                for msg in resp["Messages"]
            ],
        )
    delete_time = get_elapsed_time()
    delete_per_second = len(resp["Successful"]) / delete_time
    logging.info(
        "[Run=%i] Deleted %i messages in %03f seconds (%i / second; %i failed)",
        i,
        len(resp["Successful"]),
        delete_time,
        delete_per_second,
        len(resp["Failed"]),
    )

    return {
        "send": send_per_second,
        "receive": receive_per_second,
        "delete": delete_per_second,
    }


def main():
    args = parse_args()
    sqsc = boto3.client("sqs")
    stats = {"send": [], "receive": [], "delete": []}
    for i in range(args.iterations):
        run_stats = run_iteration(args, i, sqsc)
        stats["delete"].append(run_stats["delete"])
        stats["send"].append(run_stats["send"])
        stats["receive"].append(run_stats["receive"])

    stats["delete"].sort()
    stats["receive"].sort()
    stats["send"].sort()

    logging.info("Stats: %s", json.dumps(stats, indent=2))


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)-8s %(name)s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    main()
