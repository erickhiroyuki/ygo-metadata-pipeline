import time
from typing import Any
from urllib.parse import urlencode

from pydantic import ValidationError

from ..clients import create_http_session, get_supabase_client
from ..config import get_settings
from ..logging import get_logger
from ..models import CardMetadata, CardTranslation, RawCard, SyncResult

logger = get_logger("sync_cards")


def fetch_cards_from_api(
    cardset: str | None = None,
    language: str | None = None,
) -> list[dict[str, Any]]:

    settings = get_settings()
    params = {}

    if cardset:
        params["cardset"] = cardset
    if language:
        params["language"] = language

    if params:
        url = f"{settings.api.ygoprodeck_base_url}?{urlencode(params)}"
    else:
        url = settings.api.ygoprodeck_base_url

    log_parts = []
    if cardset:
        log_parts.append(f"set '{cardset}'")
    if language:
        log_parts.append(f"language '{language}'")

    if log_parts:
        logger.info(f"Fetching card data for {', '.join(log_parts)} from YGOProDeck API...")
    else:
        logger.info("Fetching all card data from YGOProDeck API...")

    session = create_http_session()
    response = session.get(url, timeout=60)
    response.raise_for_status()
    data = response.json()

    cards = data.get("data", [])
    logger.info(f"Successfully fetched {len(cards):,} cards from API")
    return cards


def validate_and_transform_cards(raw_cards: list[dict[str, Any]]) -> list[CardMetadata]:
    logger.info(f"Validating and transforming {len(raw_cards):,} cards...")

    transformed = []
    validation_errors = 0

    for raw in raw_cards:
        try:
            raw_card = RawCard.model_validate(raw)
            transformed.append(CardMetadata.from_raw(raw_card))
        except ValidationError as e:
            validation_errors += 1
            card_name = raw.get("name", "Unknown")
            logger.warning(f"Validation failed for card '{card_name}': {e.error_count()} errors")

    if validation_errors > 0:
        logger.warning(f"Skipped {validation_errors} cards due to validation errors")

    logger.info(f"Successfully validated {len(transformed):,} cards")
    return transformed


def validate_and_transform_translations(
    raw_cards: list[dict[str, Any]],
    language: str,
) -> list[CardTranslation]:
    logger.info(f"Validating and transforming {len(raw_cards):,} translations for '{language}'...")

    transformed = []
    validation_errors = 0

    for raw in raw_cards:
        try:
            raw_card = RawCard.model_validate(raw)
            transformed.append(CardTranslation.from_raw(raw_card, language))
        except ValidationError as e:
            validation_errors += 1
            card_name = raw.get("name", "Unknown")
            logger.warning(f"Validation failed for translation '{card_name}': {e.error_count()} errors")

    if validation_errors > 0:
        logger.warning(f"Skipped {validation_errors} translations due to validation errors")

    logger.info(f"Successfully validated {len(transformed):,} translations")
    return transformed


def batch_upsert(
    records: list[CardMetadata] | list[CardTranslation],
    table: str,
    conflict_columns: str,
) -> tuple[int, int]:
    settings = get_settings()
    client = get_supabase_client()
    batch_size = settings.pipeline.batch_size

    total = len(records)
    successful = 0
    failed = 0

    logger.info(f"Starting batch upsert of {total:,} records to '{table}' (batch size: {batch_size})")

    for i in range(0, total, batch_size):
        batch = records[i : i + batch_size]
        batch_data = [r.model_dump() for r in batch]
        batch_num = (i // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size

        try:
            client.table(table).upsert(batch_data, on_conflict=conflict_columns).execute()
            successful += len(batch)
            logger.info(
                f"Batch {batch_num}/{total_batches}: Upserted {len(batch)} records "
                f"({successful:,}/{total:,} complete)"
            )
        except Exception as e:
            failed += len(batch)
            logger.error(f"Batch {batch_num}/{total_batches}: Failed to upsert - {e}")

            for record in batch:
                try:
                    client.table(table).upsert(
                        record.model_dump(),
                        on_conflict=conflict_columns,
                    ).execute()
                    successful += 1
                    failed -= 1
                except Exception as record_error:
                    logger.error(f"Failed to upsert record '{record.name}': {record_error}")

        if i + batch_size < total:
            time.sleep(0.1)

    return successful, failed


def sync_translations(cardset: str | None = None) -> SyncResult:
    settings = get_settings()
    total_successful = 0
    total_failed = 0
    total_records = 0

    for language in settings.pipeline.translation_languages:
        logger.info("-" * 40)
        logger.info(f"Syncing translations for language: {language}")

        try:
            raw_cards = fetch_cards_from_api(cardset=cardset, language=language)
            translations = validate_and_transform_translations(raw_cards, language)

            if not translations:
                logger.warning(f"No translations found for language '{language}'")
                continue

            total_records += len(translations)
            successful, failed = batch_upsert(
                translations,
                table="ygo_card_translations",
                conflict_columns="card_id,language",
            )
            total_successful += successful
            total_failed += failed

        except Exception as e:
            logger.error(f"Failed to sync translations for '{language}': {e}")
            total_failed += 1

    return SyncResult(
        total=total_records,
        successful=total_successful,
        failed=total_failed,
    )


def run_sync_cards(
    cardset: str | None = None,
    skip_translations: bool = False,
) -> tuple[SyncResult, SyncResult | None]:
    start_time = time.time()
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("Starting YGO Card Metadata Sync")
    if cardset:
        logger.info(f"Target cardset: {cardset}")
    else:
        logger.info("Mode: Full sync (all cards)")
    if skip_translations:
        logger.info("Translations: SKIPPED")
    else:
        logger.info(f"Translations: {', '.join(settings.pipeline.translation_languages)}")
    logger.info("=" * 60)

    logger.info("Phase 1: Syncing card metadata...")
    raw_cards = fetch_cards_from_api(cardset=cardset)
    cards = validate_and_transform_cards(raw_cards)

    if not cards:
        logger.warning("No cards to process. Exiting.")
        return SyncResult(total=0, successful=0, failed=0), None

    successful, failed = batch_upsert(
        cards,
        table="ygo_card_metadata",
        conflict_columns="id",
    )

    metadata_result = SyncResult(
        total=len(cards),
        successful=successful,
        failed=failed,
        elapsed_seconds=time.time() - start_time,
    )

    translation_result = None
    if not skip_translations:
        logger.info("Phase 2: Syncing translations...")
        translation_result = sync_translations(cardset=cardset)

    elapsed = time.time() - start_time
    metadata_result.elapsed_seconds = elapsed

    logger.info("=" * 60)
    logger.info("Sync Complete!")
    logger.info(
        f"  Metadata - Total: {metadata_result.total:,}, "
        f"Success: {metadata_result.successful:,}, Failed: {metadata_result.failed:,}"
    )
    if translation_result:
        logger.info(
            f"  Translations - Total: {translation_result.total:,}, "
            f"Success: {translation_result.successful:,}, Failed: {translation_result.failed:,}"
        )
    logger.info(f"  Time elapsed: {elapsed:.2f}s")
    logger.info("=" * 60)

    return metadata_result, translation_result
