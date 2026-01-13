-- Migration: Add card detail columns to ygo_card_metadata
-- Date: 2026-01-12
-- Description: Adds columns for pendulum description, monster description,
--              attack, defense, level, attribute, and scale.
--              All columns are nullable since not all cards have this information.

ALTER TABLE public.ygo_card_metadata
ADD COLUMN IF NOT EXISTS pend_desc text NULL,
ADD COLUMN IF NOT EXISTS monster_desc text NULL,
ADD COLUMN IF NOT EXISTS atk integer NULL,
ADD COLUMN IF NOT EXISTS def integer NULL,
ADD COLUMN IF NOT EXISTS level integer NULL,
ADD COLUMN IF NOT EXISTS attribute text NULL,
ADD COLUMN IF NOT EXISTS scale integer NULL;

-- Add comment for documentation
COMMENT ON COLUMN public.ygo_card_metadata.pend_desc IS 'Pendulum effect description';
COMMENT ON COLUMN public.ygo_card_metadata.monster_desc IS 'Monster effect/flavor description';
COMMENT ON COLUMN public.ygo_card_metadata.atk IS 'Attack points';
COMMENT ON COLUMN public.ygo_card_metadata.def IS 'Defense points';
COMMENT ON COLUMN public.ygo_card_metadata.level IS 'Monster level/rank';
COMMENT ON COLUMN public.ygo_card_metadata.attribute IS 'Card attribute (DARK, LIGHT, WATER, etc.)';
COMMENT ON COLUMN public.ygo_card_metadata.scale IS 'Pendulum scale value';
