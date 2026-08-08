from pathlib import Path

from ingestion.model import NetWorth


def ingest(current: NetWorth, files: list[Path]) -> NetWorth:
    raise NotImplementedError(
        "Statement ingestion pipeline not yet implemented — "
        "extraction mechanism is a separate, later decision. "
        "This stub exists so the eval harness has a real entrypoint to call."
    )
