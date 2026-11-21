import argparse
import asyncio
import logging

from app.services.ingestion import worker_loop


def run() -> None:
    parser = argparse.ArgumentParser(description="Process Craft ingestion worker")
    parser.add_argument("--once", action="store_true", help="Drain the current queue and exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(worker_loop(once=args.once))


if __name__ == "__main__":
    run()
