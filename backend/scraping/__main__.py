import argparse
import asyncio
import logging
import sys
from pathlib import Path

from scraping.runner import run_source
from scraping.scheduler import run_worker
from scraping.sources import SOURCES
from scraping.sources.google_places import GooglePlacesCsvSource
from scraping.types import RunAlreadyInProgress, RunStatus, RunTrigger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scraping")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run one source once")
    run.add_argument("source", choices=sorted(SOURCES))
    import_places = commands.add_parser("import-places", help="load a Google Places CSV export")
    import_places.add_argument("csv_path")
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


async def _import_places(csv_path: str) -> int:
    path = Path(csv_path)
    if not path.exists():
        print(f"No such file: {path}")
        return 2
    source = GooglePlacesCsvSource(path)
    try:
        summary = await run_source("google_places", RunTrigger.MANUAL, source=source)
    except RunAlreadyInProgress as exc:
        print(exc)
        return 2
    print(
        f"status={summary.status.value} rows_kept={summary.records_seen}/{summary.expected_total} "
        f"inserted={summary.inserted} updated={summary.updated} unchanged={summary.unchanged} "
        f"parse_errors={summary.parse_errors} filtered_out={source.rejected_count}"
    )
    if source.rejected_count:
        print(f"filtered rows are listed in {path.with_name(path.stem + '.rejected.csv')}")
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
    if args.command == "import-places":
        return asyncio.run(_import_places(args.csv_path))
    return asyncio.run(_run(args.source))


if __name__ == "__main__":
    sys.exit(main())
