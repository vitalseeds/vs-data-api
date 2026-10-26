from datetime import date

from pydantic import BaseModel

from vs_data_api.vs_data.fm import db


class GermTest(BaseModel):
    date: date | None
    result: float | None
    seed_count: str | None
    notes: str | None


def _blank_to_none(value):
    """FileMaker gives '' for an empty field. A 0 is kept: it is a real result."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return value


def get_germ_tests(connection, lot_number: int) -> list[GermTest]:
    """A lot's germination tests, newest first (tests with no date last)."""
    rows = db.select(
        connection,
        "germ_tests",
        ["date", "result", "seed_count", "test_number", "notes"],
        where=f"Lot_numberFK = {int(lot_number)}",
    )
    rows.sort(key=lambda r: (r["date"] is not None, r["date"] or date.min, r["test_number"] or 0), reverse=True)
    return [
        GermTest(
            date=_blank_to_none(r["date"]),
            result=_blank_to_none(r["result"]),
            seed_count=_blank_to_none(r["seed_count"]),
            notes=_blank_to_none(r["notes"]),
        )
        for r in rows
    ]


def latest_result(tests: list[GermTest]) -> float | None:
    """Result of the latest test. None if there are no tests or the latest has no result yet."""
    return tests[0].result if tests else None
