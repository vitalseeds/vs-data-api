"""Routes for the SKU lot list (#134). Included by main.py."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import ValidationError

from vs_data_api import config, lot_page
from vs_data_api.lot_routes import FILEMAKER_DOWN, wants_json
from vs_data_api.settings import get_settings
from vs_data_api.vs_data import log
from vs_data_api.vs_data.fm import db
from vs_data_api.vs_data.lots import get_sku_lots

router = APIRouter()

MAX_SKU_LENGTH = 50


def _message(request: Request, status_code: int, title: str, message: str, sku: str = ""):
    """A plain-English error, as JSON or HTML to match what was asked for."""
    if wants_json(request):
        return JSONResponse(status_code=status_code, content={"message": message})
    return HTMLResponse(lot_page.render_message(title, message, sku, lot_page.SKU), status_code=status_code)


@router.get("/sku")
async def sku_form(sku: str | None = None):
    """Form for typing a SKU; with `?sku=X` it redirects to the SKU's page."""
    if sku and sku.strip():
        return RedirectResponse(f"/sku/{sku.strip()}", status_code=303)
    return HTMLResponse(lot_page.render_form(lot_page.SKU))


@router.get("/sku/{sku}")
async def get_sku(sku: str, request: Request, settings: config.Settings = Depends(get_settings)):
    """
    The lots in FileMaker with a SKU (case insensitive), newest received first.

    HTML by default, JSON with `?format=json` or an `Accept: application/json` header.
    """
    sku = sku.strip()
    if not sku or len(sku) > MAX_SKU_LENGTH:
        return _message(request, 422, "Not a SKU", f"'{sku[:MAX_SKU_LENGTH]}' is not a SKU.", sku[:MAX_SKU_LENGTH])

    try:
        connection = db.connection(settings.fm_connection_string)
        with connection:
            sku_lots = get_sku_lots(connection, sku)
    except ValidationError as e:
        log.error(f"Lots for SKU {sku} have a value in FileMaker that could not be read: {e}")
        message = f"A lot of SKU {sku} has a value in FileMaker that can't be read (for example text in the weight). Fix it in FileMaker."
        return _message(request, 500, "Lots can't be shown", message, sku)
    except Exception as e:
        log.error(f"Lot list for SKU {sku} failed: {e!r}")
        return _message(request, 503, "FileMaker unavailable", FILEMAKER_DOWN, sku)

    if sku_lots is None:
        return _message(request, 404, "SKU not found", f"No lots found for SKU {sku}.", sku)
    if wants_json(request):
        return sku_lots.model_dump(mode="json")
    return HTMLResponse(lot_page.render_sku(sku_lots))
