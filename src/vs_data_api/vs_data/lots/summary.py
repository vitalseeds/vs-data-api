from pydantic import BaseModel

from vs_data_api.vs_data.fm import db


class LotSummary(BaseModel):
    lot_number: int
    sku: str | None
    source: str | None
    final_weight_g: float | None


def get_lot_summary(connection, lot_number: int) -> LotSummary | None:
    """
    Look up one seed lot. Returns None when there is no such lot.

    A weight of 0 and a blank source both mean 'not recorded' and come back as None.
    """
    rows = db.select(
        connection,
        "seed_lots",
        ["lot_number", "sku", "source", "original_weight"],
        where=f"lot_number = {int(lot_number)}",
    )
    if not rows:
        return None
    row = rows[0]
    return LotSummary(
        lot_number=row["lot_number"],
        sku=row["sku"] or None,
        source=(row["source"] or "").strip() or None,
        final_weight_g=row["original_weight"] or None,
    )
