from datetime import date

from pydantic import BaseModel, field_validator

from vs_data_api.vs_data.fm import db


class SkuLot(BaseModel):
    lot_number: int
    date_received: date | None
    initial_weight_g: float | None
    current_weight_g: float | None


def _weight(value):
    """
    FileMaker's Current weight is calculated as text ("350g", or "0" for a packed lot).

    Blank is None (not recorded). Zero is kept: it is a real value, and means the lot is used up.
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value.lower().endswith("g"):
            value = value[:-1].strip()
        if not value:
            return None
    return value


class SkuLots(BaseModel):
    sku: str
    lots: list[SkuLot]


class _SkuLotRow(BaseModel):
    lot_number: int
    sku: str
    date_received: date | None
    original_weight: float | None
    current_weight: float | None

    @field_validator("date_received", mode="before")
    @classmethod
    def _blank_date(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("original_weight", "current_weight", mode="before")
    @classmethod
    def _blank_weight(cls, value):
        return _weight(value)


def _quote(text: str) -> str:
    """Escape for a single-quoted SQL string. db.select has no parameter binding."""
    return text.replace("'", "''")


def get_sku_lots(connection, sku: str) -> SkuLots | None:
    """
    The lots with this SKU, case insensitive, newest received first (undated last).

    Returns None when no lot has the SKU. The SKU is as stored in FileMaker, not as typed.
    A weight of 0 is kept, a blank one is None.
    """
    rows = db.select(
        connection,
        "seed_lots",
        ["lot_number", "sku", "date_received", "original_weight", "current_weight"],
        where=f"UPPER(\"sku\") = '{_quote(sku.strip().upper())}'",
    )
    if not rows:
        return None
    parsed = [_SkuLotRow(**row) for row in rows]
    # Undated lots last; for the same date the higher (later) lot number first
    parsed.sort(key=lambda r: (r.date_received is not None, r.date_received or date.min, r.lot_number), reverse=True)
    return SkuLots(
        sku=parsed[0].sku,
        lots=[
            SkuLot(
                lot_number=r.lot_number,
                date_received=r.date_received,
                initial_weight_g=r.original_weight or None,
                current_weight_g=r.current_weight,
            )
            for r in parsed
        ],
    )
