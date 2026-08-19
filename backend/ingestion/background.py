import asyncio
import shutil
from decimal import Decimal
from pathlib import Path

from database.repository import IngestionRunRepository
from database.session import session_context
from ingestion.persistence import load_current_networth, persist_networth
from ingestion.pipeline import ingest


async def run_ingestion(
    run_id: str,
    user_id: str,
    file_paths: list[Path],
    password: str | None,
    reporting_currency: str,
    passwords: dict[str, str] | None = None,
) -> None:
    try:
        async with session_context() as session:
            await IngestionRunRepository(session).mark_processing(run_id)

        async with session_context() as session:
            current = await load_current_networth(session, user_id, reporting_currency)
            # ingest() is a plain synchronous function that may make live, multi-
            # second LLM calls — offloaded to a thread so it doesn't block the
            # event loop from serving other requests while this run is in flight.
            result = await asyncio.to_thread(ingest, current, file_paths, password, passwords)
            positions_count, warnings = await persist_networth(session, run_id, user_id, result)
            usage = result.llm_usage
            await IngestionRunRepository(session).mark_succeeded(
                run_id,
                positions_count,
                warnings,
                llm_call_count=usage.call_count if usage else None,
                llm_input_tokens=usage.input_tokens if usage else None,
                llm_output_tokens=usage.output_tokens if usage else None,
                llm_cache_creation_tokens=usage.cache_creation_input_tokens if usage else None,
                llm_cache_read_tokens=usage.cache_read_input_tokens if usage else None,
                llm_estimated_cost_usd=(
                    Decimal(str(usage.estimated_cost_usd))
                    if usage and usage.estimated_cost_usd is not None
                    else None
                ),
            )
    except Exception as exc:
        async with session_context() as session:
            await IngestionRunRepository(session).mark_failed(run_id, str(exc))
    finally:
        # All of one run's files share one per-request temp directory (see
        # api/ingestion_api.py) — remove it wholesale rather than unlinking each
        # file individually, so the directory itself doesn't linger either.
        if file_paths:
            shutil.rmtree(file_paths[0].parent, ignore_errors=True)
