-- Migration: Create ygo_banlist table
-- Date: 2026-01-13
-- Description: Creates a table to store banlist information for cards in TCG and OCG formats.
--              Ban status values: 'Forbidden' (0 copies), 'Limited' (1 copy), 'Semi-Limited' (2 copies)

CREATE TABLE IF NOT EXISTS public.ygo_banlist (
    card_id integer PRIMARY KEY,
    card_name text NOT NULL,
    ban_tcg text NULL,
    ban_ocg text NULL,
    ban_goat text NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

-- Add comments for documentation
COMMENT ON TABLE public.ygo_banlist IS 'Stores banlist status for Yu-Gi-Oh! cards across different formats';
COMMENT ON COLUMN public.ygo_banlist.card_id IS 'Card ID from YGOProDeck (references ygo_card_metadata.id)';
COMMENT ON COLUMN public.ygo_banlist.card_name IS 'Card name for easier querying';
COMMENT ON COLUMN public.ygo_banlist.ban_tcg IS 'TCG banlist status: Forbidden, Limited, or Semi-Limited';
COMMENT ON COLUMN public.ygo_banlist.ban_ocg IS 'OCG banlist status: Forbidden, Limited, or Semi-Limited';
COMMENT ON COLUMN public.ygo_banlist.ban_goat IS 'GOAT format banlist status: Forbidden, Limited, or Semi-Limited';
COMMENT ON COLUMN public.ygo_banlist.updated_at IS 'Last time this record was updated';

-- Create index for faster lookups by ban status
CREATE INDEX IF NOT EXISTS idx_ygo_banlist_ban_tcg ON public.ygo_banlist (ban_tcg) WHERE ban_tcg IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ygo_banlist_ban_ocg ON public.ygo_banlist (ban_ocg) WHERE ban_ocg IS NOT NULL;

-- Enable Row Level Security (disabled by default, can be enabled if needed)
-- ALTER TABLE public.ygo_banlist ENABLE ROW LEVEL SECURITY;
