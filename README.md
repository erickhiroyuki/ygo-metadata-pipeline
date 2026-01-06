# YGO Pipeline

Data ingestion pipelines for Yu-Gi-Oh! card metadata, translations, and images.

## Overview

This project synchronizes card data from the [YGOProDeck API](https://ygoprodeck.com/api-guide/) to a Supabase database and AWS S3 for image storage.

## Installation

```bash
uv sync
```

Required environment variables:

| Variable | Description |
|----------|-------------|
| `SUPABASE_DB_URL` | Supabase project URL |
| `SUPABASE_DB_KEY` | Supabase service role key |
| `AWS_REGION` | AWS region for S3 |
| `AWS_BUCKET_NAME` | S3 bucket name for images |
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |

## Usage

### Sync Card Metadata

```bash
# Sync all cards and translations
uv run main.py sync-cards

# Sync specific card set
uv run main.py sync-cards --cardset "Justice Hunters"

# Sync metadata only (skip translations)
uv run main.py sync-cards --skip-translations
```

### Sync Card Images

```bash
# Sync images (only cards missing S3 URLs)
uv run main.py sync-images

# Force re-upload all images
uv run main.py sync-images --force

# Limit to first 100 cards (for testing)
uv run main.py sync-images --limit 100

# Use more workers for faster uploads
uv run main.py sync-images --workers 20
```

### Advanced Options

```bash
# JSON logs (for production/logging systems)
uv run main.py --json-logs sync-cards

# Debug logging
uv run main.py --debug sync-images
```
