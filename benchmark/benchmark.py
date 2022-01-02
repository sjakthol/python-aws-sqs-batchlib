import argparse
import concurrent.futures
import contextlib
import json
import logging
import threading
import time

import aws_sqs_batchlib
import botocore.session  # type: ignore
import pyformance  # type: ignore


def get_client():
    """Get SQS client."""
    session = botocore.session.get_session()
    return session.create_client("sqs")


@contextlib.contextmanager
def stopwatch():
    """Measure runtime of a block of code.

    >>> with _stopwatch() as get_elapsed_time:
    ...     pass
    >>> runtime = get_elapsed_time()
    """
    start = time.perf_counter()
    yield lambda: time.perf_counter() - start


def consumer_plain(args, stop_event):
    """Consume given SQS queue until stop signal arrives."""
    sqs = get_client()

    while not stop_event.is_set():
        with stopwatch() as get_elapsed_time:
            res = sqs.receive_message(
                QueueUrl=args.queue_url,
                MaxNumberOfMessages=10,
            )

        latency = get_elapsed_time()

        pyformance.counter("received").inc(len(res.get("Messages", {})))
        pyformance.histogram("latency").add(latency)


def consumer_lib(args, stop_event):
    while not stop_event.is_set():
        with stopwatch() as get_elapsed_time:
            res = aws_sqs_batchlib.receive_message(
                QueueUrl=args.queue_url, MaxNumberOfMessages=args.batch_size, WaitTimeSeconds=args.batch_window,
            )
        latency = get_elapsed_time()

        logging.info(
            "Got batch of %i messages in %.3f seconds",
            len(res.get("Messages", {})),
            latency,
        )
        pyformance.counter("received").inc(len(res.get("Messages", {})))
        pyformance.histogram("latency").add(latency)


def producer(args, stop_event):
    """Produce messages to given SQS queue until stop signal arrives."""
    entries = [{"Id": str(i), "MessageBody": "A" * 10 * 1024} for i in range(10)]

    sqs = get_client()

    while not stop_event.is_set():
        with stopwatch() as get_elapsed_time:
            res = sqs.send_message_batch(
                QueueUrl=args.queue_url,
                Entries=entries,
            )

        latency = get_elapsed_time()

        pyformance.counter("sent").inc(len(entries))
        pyformance.counter("success").inc(len(res.get("Successful", [])))
        pyformance.counter("failed").inc(len(res.get("Failed", [])))
        pyformance.histogram("latency").add(latency)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--queue-url",
        type=str,
        help="Queue to write data to",
        required=True,
    )
    parser.add_argument(
        "-p",
        "--parallelism",
        type=int,
        help="Number of parallel producer threads to run",
        default=1,
    )

    parser.add_argument(
        "action", choices=("producer", "consumer-plain", "consumer-lib")
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        help="Number of messages to consume per iteration. For consumer-lib only.",
        default=100,
    )
    parser.add_argument(
        "-w",
        "--batch-window",
        type=int,
        help="Maximum number of seconds to collect messages to a single batch. For consumer-lib only.",
        default=1,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    actions = {
        "producer": producer,
        "consumer-plain": consumer_plain,
        "consumer-lib": consumer_lib,
    }

    stop_event = threading.Event()
    with concurrent.futures.ThreadPoolExecutor(args.parallelism) as tpe:
        futures = [
            tpe.submit(actions[args.action], args, stop_event)
            for _ in range(args.parallelism)
        ]

        try:
            while futures:
                done, futures = concurrent.futures.wait(futures, timeout=1.0)
                metrics = pyformance.dump_metrics()
                metrics["latency"] = {
                    k: round(v, 3) for k, v in metrics.get("latency", {}).items()
                }
                logging.info("Metrics: %s", json.dumps(metrics))
                pyformance.clear()

                [f.result() for f in done]
        finally:
            stop_event.set()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)-8s %(name)s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    main()
