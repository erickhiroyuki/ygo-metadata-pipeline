"""Sync banlist data from YGOProDeck API."""
import time
from typing import Any

from pydantic import BaseModel

from ..clients import create_http_session, get_supabase_client
from ..config import get_settings
from ..logging import get_logger
from ..models import SyncResult

logger = get_logger("sync_banlist")


class BanlistInfo(BaseModel):
    """Banlist information for a card."""

    ban_tcg: str | None = None
    ban_ocg: str | None = None
    ban_goat: str | None = None


class CardBanlistEntry(BaseModel):
    """A single card's banlist entry."""

    card_id: int
    card_name: str
    ban_tcg: str | None = None
    ban_ocg: str | None = None
    ban_goat: str | None = None


def fetch_banlist_from_api() -> list[dict[str, Any]]:
    """Fetch cards with banlist info from YGOProDeck API."""
    settings = get_settings()
    url = f"{settings.api.ygoprodeck_base_url}?banlist=tcg"

    logger.info("Fetching banlist data from YGOProDeck API...")

    session = create_http_session()
    response = session.get(url, timeout=60)
    response.raise_for_status()
    data = response.json()

    cards = data.get("data", [])
    logger.info(f"Successfully fetched {len(cards):,} cards from banlist API")
    return cards


def extract_banlist_entries(raw_cards: list[dict[str, Any]]) -> list[CardBanlistEntry]:
    """Extract banlist information from raw card data."""
    logger.info(f"Processing {len(raw_cards):,} cards for banlist entries...")

    entries = []

    for card in raw_cards:
        banlist_info = card.get("banlist_info")
        if not banlist_info:
            continue

        entry = CardBanlistEntry(
            card_id=card["id"],
            card_name=card["name"],
            ban_tcg=banlist_info.get("ban_tcg"),
            ban_ocg=banlist_info.get("ban_ocg"),
            ban_goat=banlist_info.get("ban_goat"),
        )
        entries.append(entry)

    logger.info(f"Found {len(entries):,} cards with banlist restrictions")

    # Log summary by status
    tcg_forbidden = sum(1 for e in entries if e.ban_tcg == "Forbidden")
    tcg_limited = sum(1 for e in entries if e.ban_tcg == "Limited")
    tcg_semi_limited = sum(1 for e in entries if e.ban_tcg == "Semi-Limited")

    logger.info(
        f"TCG Banlist Summary - Forbidden: {tcg_forbidden}, "
        f"Limited: {tcg_limited}, Semi-Limited: {tcg_semi_limited}"
    )

    return entries


def batch_upsert_banlist(entries: list[CardBanlistEntry]) -> tuple[int, int]:
    """Upsert banlist entries to the database."""
    settings = get_settings()
    client = get_supabase_client()
    batch_size = settings.pipeline.batch_size

    total = len(entries)
    successful = 0
    failed = 0

    logger.info(f"Starting batch upsert of {total:,} banlist records (batch size: {batch_size})")

    for i in range(0, total, batch_size):
        batch = entries[i : i + batch_size]
        batch_data = [e.model_dump() for e in batch]
        batch_num = (i // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size

        try:
            client.table("ygo_banlist").upsert(batch_data, on_conflict="card_id").execute()
            successful += len(batch)
            logger.info(
                f"Batch {batch_num}/{total_batches}: Upserted {len(batch)} records "
                f"({successful:,}/{total:,} complete)"
            )
        except Exception as e:
            failed += len(batch)
            logger.error(f"Batch {batch_num}/{total_batches}: Failed to upsert - {e}")

            # Retry individual records on batch failure
            for entry in batch:
                try:
                    client.table("ygo_banlist").upsert(
                        entry.model_dump(),
                        on_conflict="card_id",
                    ).execute()
                    successful += 1
                    failed -= 1
                except Exception as record_error:
                    logger.error(f"Failed to upsert banlist for '{entry.card_name}': {record_error}")

        if i + batch_size < total:
            time.sleep(0.1)

    return successful, failed


def run_sync_banlist() -> SyncResult:
    """Run the banlist synchronization pipeline."""
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("Starting YGO Banlist Sync")
    logger.info("=" * 60)

    # Fetch data from API
    raw_cards = fetch_banlist_from_api()

    # Extract banlist entries
    entries = extract_banlist_entries(raw_cards)

    if not entries:
        logger.warning("No banlist entries to process. Exiting.")
        return SyncResult(total=0, successful=0, failed=0)

    # Upsert to database
    successful, failed = batch_upsert_banlist(entries)

    elapsed = time.time() - start_time

    result = SyncResult(
        total=len(entries),
        successful=successful,
        failed=failed,
        elapsed_seconds=elapsed,
    )

    logger.info("=" * 60)
    logger.info("Banlist Sync Complete!")
    logger.info(
        f"  Total: {result.total:,}, Success: {result.successful:,}, Failed: {result.failed:,}"
    )
    logger.info(f"  Time elapsed: {elapsed:.2f}s")
    logger.info("=" * 60)

    return result
