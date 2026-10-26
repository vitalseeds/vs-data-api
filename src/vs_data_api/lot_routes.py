"""Routes for the lot summary page (#132). Included by main.py."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from vs_data_api import config, lot_page
from vs_data_api.main import get_settings
from vs_data_api.vs_data import log
from vs_data_api.vs_data.fm import db
from vs_data_api.vs_data.lots import get_lot_summary

router = APIRouter()

MAX_LOT_NUMBER = 2147483647
FILEMAKER_DOWN = "Can't reach FileMaker right now. Check that FileMaker is open on the office PC."


def _wants_json(request: Request) -> bool:
    return request.query_params.get("format") == "json" or "application/json" in request.headers.get("accept", "")


def _message(request: Request, status_code: int, title: str, message: str):
    """A plain-English error, as JSON or HTML to match what was asked for."""
    if _wants_json(request):
        return JSONResponse(status_code=status_code, content={"message": message})
    return HTMLResponse(lot_page.render_message(title, message), status_code=status_code)


def _parse_lot_number(raw: str) -> int | None:
    try:
        number = int(raw.strip())
    except ValueError:
        return None
    return number if 0 < number <= MAX_LOT_NUMBER else None


@router.get("/lot")
async def lot_form(lot_number: str | None = None):
    """Form for typing a lot number; with `?lot_number=N` it redirects to the lot's page."""
    if lot_number:
        return RedirectResponse(f"/lot/{lot_number.strip()}", status_code=303)
    return HTMLResponse(lot_page.render_form())


@router.get("/lot/{lot_number}")
async def get_lot(lot_number: str, request: Request, settings: config.Settings = Depends(get_settings)):
    """
    Summary of one seed lot from FileMaker: SKU, source and final weight.

    HTML by default, JSON with `?format=json` or an `Accept: application/json` header.
    """
    number = _parse_lot_number(lot_number)
    if number is None:
        return _message(request, 422, "Not a lot number", f"'{lot_number}' is not a lot number. Use a whole number.")

    try:
        connection = db.connection(settings.fm_connection_string)
        with connection:
            summary = get_lot_summary(connection, number)
    except Exception as e:
        log.error(f"Lot summary for {number} failed: {e!r}")
        return _message(request, 503, "FileMaker unavailable", FILEMAKER_DOWN)

    if summary is None:
        return _message(request, 404, "Lot not found", f"Lot {number} not found.")
    if _wants_json(request):
        return summary.model_dump()
    return HTMLResponse(lot_page.render_lot(summary))
