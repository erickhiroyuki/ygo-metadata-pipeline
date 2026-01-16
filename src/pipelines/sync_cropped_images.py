import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from botocore.exceptions import ClientError
from PIL import Image

from ..clients import create_http_session, create_s3_client, get_supabase_client
from ..config import get_settings
from ..logging import get_logger
from ..models import SyncResult

logger = get_logger("sync_cropped_images")

RESIZE_FACTOR = 0.6


def get_cards_without_cropped_images(force: bool = False, limit: int | None = None) -> list[dict]:
    client = get_supabase_client()
    logger.info("Fetching cards from database...")

    all_cards = []
    page_size = 1000
    offset = 0

    while True:
        query = client.table("ygo_card_metadata").select("id, name")

        if not force:
            query = query.is_("image_cropped_url_s3", "null")

        query = query.range(offset, offset + page_size - 1)
        response = query.execute()
        cards = response.data

        if not cards:
            break

        all_cards.extend(cards)
        logger.info(f"Fetched {len(all_cards):,} cards so far...")

        if len(cards) < page_size:
            break

        offset += page_size

        if limit and len(all_cards) >= limit:
            all_cards = all_cards[:limit]
            break

    logger.info(f"Found {len(all_cards):,} cards to process")
    return all_cards


def download_cropped_image(card_id: int, session: requests.Session) -> bytes | None:
    settings = get_settings()
    url = settings.api.ygoprodeck_cropped_image_template.format(card_id=card_id)

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to download cropped image for card {card_id}: {e}")
        return None


def resize_image(image_data: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_data))

    new_width = int(img.width * RESIZE_FACTOR)
    new_height = int(img.height * RESIZE_FACTOR)

    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    output = io.BytesIO()
    resized_img.save(output, format="JPEG", quality=85, optimize=True)
    output.seek(0)

    return output.getvalue()


def upload_cropped_to_s3(card_id: int, image_data: bytes, s3_client) -> str | None:
    settings = get_settings()
    key = f"cards_cropped/{card_id}.jpg"

    try:
        s3_client.put_object(
            Bucket=settings.aws.bucket_name,
            Key=key,
            Body=image_data,
            ContentType="image/jpeg",
        )

        s3_url = f"https://{settings.aws.bucket_name}.s3.{settings.aws.region}.amazonaws.com/{key}"
        return s3_url
    except ClientError as e:
        logger.error(f"Failed to upload cropped image for card {card_id} to S3: {e}")
        return None


def update_database_cropped(card_id: int, s3_url: str) -> bool:
    client = get_supabase_client()

    try:
        client.table("ygo_card_metadata").update({"image_cropped_url_s3": s3_url}).eq(
            "id", card_id
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update database for card {card_id}: {e}")
        return False


def process_card(
    card: dict,
    session: requests.Session,
    s3_client,
) -> tuple[int, bool, str | None]:
    card_id = card["id"]
    card_name = card["name"]

    image_data = download_cropped_image(card_id, session)
    if not image_data:
        return card_id, False, f"Failed to download cropped image for '{card_name}'"

    try:
        resized_data = resize_image(image_data)
    except Exception as e:
        return card_id, False, f"Failed to resize image for '{card_name}': {e}"

    s3_url = upload_cropped_to_s3(card_id, resized_data, s3_client)
    if not s3_url:
        return card_id, False, f"Failed to upload cropped image for '{card_name}' to S3"

    if not update_database_cropped(card_id, s3_url):
        return card_id, False, f"Failed to update database for '{card_name}'"

    return card_id, True, None


def process_cards_parallel(cards: list[dict], max_workers: int) -> tuple[int, int]:
    successful = 0
    failed = 0
    total = len(cards)

    session = create_http_session()
    s3_client = create_s3_client()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_card, card, session, s3_client): card for card in cards
        }

        for i, future in enumerate(as_completed(futures), 1):
            card = futures[future]
            try:
                card_id, success, error_msg = future.result()
                if success:
                    successful += 1
                else:
                    failed += 1
                    if error_msg:
                        logger.warning(error_msg)
            except Exception as e:
                failed += 1
                logger.error(f"Unexpected error processing card {card['id']}: {e}")

            if i % 100 == 0 or i == total:
                logger.info(
                    f"Progress: {i:,}/{total:,} cards processed "
                    f"({successful:,} success, {failed:,} failed)"
                )

    return successful, failed


def run_sync_cropped_images(
    force: bool = False,
    limit: int | None = None,
    workers: int | None = None,
) -> SyncResult:
    settings = get_settings()
    start_time = time.time()

    if workers is None:
        workers = settings.pipeline.max_workers

    logger.info("=" * 60)
    logger.info("Starting YGO Cropped Card Image Sync to S3")
    logger.info(f"S3 Bucket: {settings.aws.bucket_name}")
    logger.info(f"Region: {settings.aws.region}")
    logger.info(f"Force re-upload: {force}")
    logger.info(f"Parallel workers: {workers}")
    logger.info(f"Image resize factor: {RESIZE_FACTOR} (40% size reduction)")
    if limit:
        logger.info(f"Limit: {limit} cards")
    logger.info("=" * 60)

    cards = get_cards_without_cropped_images(force=force, limit=limit)

    if not cards:
        logger.info("No cards to process. All cropped images are already synced!")
        return SyncResult(total=0, successful=0, failed=0, elapsed_seconds=0)

    successful, failed = process_cards_parallel(cards, workers)

    elapsed = time.time() - start_time

    logger.info("=" * 60)
    logger.info("Sync Complete!")
    logger.info(f"  Total cards: {len(cards):,}")
    logger.info(f"  Successful: {successful:,}")
    logger.info(f"  Failed: {failed:,}")
    logger.info(f"  Time elapsed: {elapsed:.2f}s")
    if successful > 0:
        logger.info(f"  Average: {elapsed/successful:.2f}s per card")
    logger.info("=" * 60)

    return SyncResult(
        total=len(cards),
        successful=successful,
        failed=failed,
        elapsed_seconds=elapsed,
    )
