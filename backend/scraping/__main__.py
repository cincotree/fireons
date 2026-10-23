import argparse
import asyncio
import logging
import sys

from scraping.runner import run_source
from scraping.scheduler import run_worker
from scraping.sources import SOURCES
from scraping.types import RunAlreadyInProgress, RunStatus, RunTrigger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scraping")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run one source once")
    run.add_argument("source", choices=sorted(SOURCES))
    commands.add_parser("worker", help="run the scheduler in the foreground")
    commands.add_parser("list", help="list available sources")
    return parser


async def _run(source: str) -> int:
    try:
        summary = await run_source(source, RunTrigger.MANUAL)
    except RunAlreadyInProgress as exc:
        print(exc)
        return 2
    print(
        f"status={summary.status.value} pages={summary.pages_fetched} "
        f"seen={summary.records_seen}/{summary.expected_total} inserted={summary.inserted} "
        f"updated={summary.updated} unchanged={summary.unchanged} "
        f"parse_errors={summary.parse_errors} delisted={summary.marked_delisted}"
    )
    if summary.error:
        print(f"error: {summary.error}")
    return 0 if summary.status == RunStatus.SUCCEEDED else 1


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    args = build_parser().parse_args(argv)
    if args.command == "list":
        print("\n".join(sorted(SOURCES)))
        return 0
    if args.command == "worker":
        asyncio.run(run_worker())
        return 0
    return asyncio.run(_run(args.source))


if __name__ == "__main__":
    sys.exit(main())
