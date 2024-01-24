from datetime import datetime
from functools import lru_cache

from fastapi import Depends, FastAPI
from starlette.responses import FileResponse

from vs_data_api import config
from vs_data_api.vs_data import orders, products, stock, wc
from vs_data_api.vs_data.fm import db

app = FastAPI(title="VS Data API")


@lru_cache()
def get_settings():
    return config.Settings()


# def has_settings(func):
#     def wrap_and_call(*args, **kwargs):
#         return func(settings:config.Settings=Depends(get_settings), *args, **kwargs)
#     return wrap_and_call


from fastapi import Request
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def vsdata_exception_handler(request: Request, exc: Exception):
    from textwrap import dedent

    # Return a parseable message to Filemaker
    return JSONResponse(
        status_code=500,
        content={
            "message": dedent(
                f"""
                Filemaker requested an action from vsdata (python),
                but an error occurred.

                {request.method}: {request.url}

                Error message:
                {exc!r}.
                """
            )
        },
    )


@app.get("/")
async def root():
    """
    Tests that API is running and accepting requests
    """
    return {"message": "VS Data API running"}


@app.get("/product/{product_id}")
async def get_product_by_id(product_id: int, settings: config.Settings = Depends(get_settings)):
    """
    Gets a product from the aquisitions table

    Currently unnused stub.
    """
    return {"product": product_id}


@app.get("/batch/awaiting_upload")
async def get_awaiting_upload(settings: config.Settings = Depends(get_settings)):
    """
    Gets batches that are awaiting upload to store
    """
    connection = db.connection(settings.fm_connection_string)
    batches = stock.get_batches_awaiting_upload_join_acq(connection)
    return {"batches": batches}


@app.get("/batch/upload-wc-stock")
async def upload_wc_stock(settings: config.Settings = Depends(get_settings)):
    """
    Increment stock for batches awaiting upload
    """
    connection = db.connection(settings.fm_connection_string)
    batches = stock.update_wc_stock_for_new_batches(connection, settings.wcapi)
    # TODO: check for wordpress hangups
    # TODO: better response messages (to show in Filemaker)
    if not batches:
        return {"message": "No batches were updated on WooCommerce"}
    updated_num = len(batches)
    return {"batches": batches, "message": f"{updated_num} products were updated on WooCommerce"}


@app.get("/batch/upload-wc-stock/variation/large")
async def upload_wc_stock_variation_large(settings: config.Settings = Depends(get_settings)):
    """
    Increment stock for *large packet* batches awaiting upload.

    This involves setting the stock level on the product *variation*, rather than the
    main product.
    """
    connection = db.connection(settings.fm_connection_string)
    batches = stock.update_wc_stock_for_new_batches(connection, settings.wcapi, product_variation="large")
    if not batches:
        return {"message": "No large batches were updated on WooCommerce"}
    updated_num = len(batches)
    return {"batches": batches, "message": f"{updated_num} product variations were updated on WooCommerce"}


@app.get("/stock/report/all")
async def download(clear_cache: bool = True, settings: config.Settings = Depends(get_settings)):
    """
    Query stock values:
    - filemaker
    - all WooCommerce products
    - all WC large product variations

    Aggregates all stock information into a CSV report for download.

    Warning: the variations aspect makes reporting very slow.
    Use querystring param `clear_cache=false` to serve up the last generated
    report instead (fast).
    """
    connection = db.connection(settings.fm_connection_string)
    export_file_path = stock.compare_wc_fm_stock(connection, settings.wcapi, csv=True, uncache=clear_cache)
    date_suffix = datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    file_name = f"vsdata_stock-report-all_{date_suffix}.csv"
    return FileResponse(path=export_file_path, filename=file_name, media_type="text/csv")


@app.get("/orders/selected/update/status/{target_status}")
async def update_status_selected_orders(target_status: str, settings: config.Settings = Depends(get_settings)):
    """
    Update order statuses.

    - queries link database for orders that are marked as 'selected'
    - posts a bulk update to woocommerce for those orders
    - updates status and deselects orders in link database
    """
    fmlinkdb = db.connection(settings.fm_link_connection_string)
    updated_orders = orders.update_packed_orders_status(fmlinkdb, settings.wcapi, target_status=target_status)

    if updated_orders and isinstance(updated_orders, list):
        num_orders = len(updated_orders)
        return {"orders": updated_orders, "message": f"{num_orders} orders were updated on WooCommerce"}

    return {"message": "No orders were updated on WooCommerce."}


@app.get("/products/variations/update-wc-price")
async def update_wc_variation_prices(settings: config.Settings = Depends(get_settings)):
    """
    Update WooCommerce price for product variations from our database
    """
    connection = db.connection(settings.fm_connection_string)
    variations, audit_log_path = products.push_variation_prices_to_wc(settings.wcapi, connection)

    if not variations:
        return {"message": "No variations were updated on WooCommerce"}
    updated_num = len(variations)
    return {
        "variations": variations,
        "message": f"{updated_num} products were updated on WooCommerce. \nSee {audit_log_path} for details",
    }


@app.get("/stock/apply-corrections")
async def apply_stock_corrections_wc(settings: config.Settings = Depends(get_settings)):
    """
    Apply stock corrections detailed in VS database to WC products and variations.
    """
    connection = db.connection(settings.fm_connection_string)
    with connection:
        applied_corrections = stock.apply_corrections_to_wc_stock(connection, settings.wcapi)
        if not applied_corrections:
            return {"message": "No corrections were applied to WooCommerce"}
        return {
            "applied_corrections": applied_corrections,
            "message": f"{len(applied_corrections)} stock corrections were applied to WooCommerce products/variations.",
        }


@app.get("/orders/wholesale/export/{order_id}")
async def export_wholesale_orders(order_id: str, settings: config.Settings = Depends(get_settings)):
    """
    Export wholesale orders as CSV for import into Xero
    """
    fmlinkdb = db.connection(settings.fm_link_connection_string)

    exported_orders = orders.wholesale.export_wholesale_orders(fmlinkdb, order_id, cli=True)

    return {"message": "No orders were updated on WooCommerce."}
