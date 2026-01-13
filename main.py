#!/usr/bin/env python3
import argparse
import sys

from src.logging import setup_logging
from src.pipelines import run_sync_banlist, run_sync_cards, run_sync_images


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="ygo-pipelines",
        description="Yu-Gi-Oh! card data synchronization pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run main.py sync-cards                    # Sync all cards and translations
  uv run main.py sync-cards -c "Justice Hunters"  # Sync specific set
  uv run main.py sync-cards --skip-translations   # Sync metadata only
  uv run main.py sync-images                   # Sync images to S3
  uv run main.py sync-images --force -l 100    # Force re-upload first 100
  uv run main.py sync-banlist                  # Sync TCG banlist data
        """,
    )

    parser.add_argument(
        "--json-logs",
        action="store_true",
        help="Output logs in JSON format (useful for production)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    cards_parser = subparsers.add_parser(
        "sync-cards",
        help="Sync card metadata and translations from YGOProDeck API",
    )
    cards_parser.add_argument(
        "--cardset",
        "-c",
        type=str,
        default=None,
        help="Optional card set name to sync (e.g., 'Justice Hunters')",
    )
    cards_parser.add_argument(
        "--skip-translations",
        action="store_true",
        help="Skip syncing translations (only sync metadata)",
    )

    images_parser = subparsers.add_parser(
        "sync-images",
        help="Sync card images from YGOProDeck to AWS S3",
    )
    images_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force re-upload of all images, even if they already exist in S3",
    )
    images_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Limit the number of cards to process (useful for testing)",
    )
    images_parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=None,
        help="Number of parallel workers for uploading (default: 10)",
    )

    subparsers.add_parser(
        "sync-banlist",
        help="Sync banlist data (Forbidden/Limited/Semi-Limited) from YGOProDeck API",
    )

    return parser


def cmd_sync_cards(args: argparse.Namespace) -> int:
    metadata_result, translation_result = run_sync_cards(
        cardset=args.cardset,
        skip_translations=args.skip_translations,
    )

    if metadata_result.failed > 0:
        return 1
    if translation_result and translation_result.failed > 0:
        return 1
    return 0


def cmd_sync_images(args: argparse.Namespace) -> int:
    result = run_sync_images(
        force=args.force,
        limit=args.limit,
        workers=args.workers,
    )

    return 1 if result.failed > 0 else 0


def cmd_sync_banlist(args: argparse.Namespace) -> int:
    result = run_sync_banlist()
    return 1 if result.failed > 0 else 0


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=log_level, json_format=args.json_logs)

    commands = {
        "sync-banlist": cmd_sync_banlist,
        "sync-cards": cmd_sync_cards,
        "sync-images": cmd_sync_images,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
