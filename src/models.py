from typing import Any

from pydantic import BaseModel, Field


class CardSet(BaseModel):
    set_name: str
    set_code: str
    set_rarity: str | None = None
    set_rarity_code: str | None = None
    set_price: str | None = None


class RawCard(BaseModel):
    id: int
    name: str
    desc: str | None = Field(default=None, alias="desc")
    type: str | None = None
    frameType: str | None = None
    race: str | None = None
    archetype: str | None = None
    card_sets: list[dict[str, Any]] | None = None

    model_config = {"populate_by_name": True}


class CardMetadata(BaseModel):
    id: int
    name: str
    description: str | None = None
    type: str | None = None
    frame_type: str | None = None
    race: str | None = None
    archetype: str | None = None
    details: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: RawCard) -> "CardMetadata":
        return cls(
            id=raw.id,
            name=raw.name,
            description=raw.desc,
            type=raw.type,
            frame_type=raw.frameType,
            race=raw.race,
            archetype=raw.archetype,
            details=raw.card_sets or [],
        )


class CardTranslation(BaseModel):
    card_id: int
    language: str
    name: str
    description: str | None = None

    @classmethod
    def from_raw(cls, raw: RawCard, language: str) -> "CardTranslation":
        return cls(
            card_id=raw.id,
            language=language,
            name=raw.name,
            description=raw.desc,
        )


class CardImage(BaseModel):
    id: int
    name: str
    image_url_s3: str | None = None


class SyncResult(BaseModel):
    total: int
    successful: int
    failed: int
    skipped: int = 0
    elapsed_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 100.0
        return (self.successful / self.total) * 100
