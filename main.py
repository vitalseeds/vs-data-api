from functools import lru_cache
from datetime import datetime
from fastapi import Depends, FastAPI
from starlette.responses import FileResponse

from vs_data.fm import db
from vs_data import stock
from vs_data import wc
from vs_data import orders


import config

app = FastAPI(
    title="VS Data API"
)


@lru_cache()
def get_settings():
    return config.Settings()


# def has_settings(func):
#     def wrap_and_call(*args, **kwargs):
#         return func(settings:config.Settings=Depends(get_settings), *args, **kwargs)
#     return wrap_and_call


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
async def download(settings: config.Settings = Depends(get_settings)):
    """
    Query filemaker then all WooCommerce products, then all WC large product
    variations. Warning: the variations aspect makes this quite slow.

    Aggregate all stock information into a CSV report.
    """
    connection = db.connection(settings.fm_connection_string)
    export_file_path = stock.compare_wc_fm_stock(connection, settings.wcapi, csv=True, uncache=True)
    date_suffix = datetime.now().strftime('%m-%d-%Y_%H-%M-%S')
    file_name = f"vsdata_stock-report-all_{date_suffix}.csv"
    return FileResponse(path=export_file_path, filename=file_name, media_type='text/csv')


@app.get("/stock/report/all/cached")
async def download_cached(settings: config.Settings = Depends(get_settings)):
    """
    Query filemaker then all WooCommerce products, then all WC large product
    variations. Warning: the variations aspect makes this quite slow.

    Aggregate all stock information into a CSV report.
    """
    connection = db.connection(settings.fm_connection_string)
    export_file_path = stock.compare_wc_fm_stock(connection, settings.wcapi, csv=True, uncache=False)
    date_suffix = datetime.now().strftime('%m-%d-%Y_%H-%M-%S')
    file_name = f"vsdata_stock-report-all_{date_suffix}.csv"
    return FileResponse(path=export_file_path, filename=file_name, media_type='text/csv')


@app.get("/orders/selected/update/status/{target_status}")
async def update_status_selected_orders(target_status:str, settings: config.Settings = Depends(get_settings)):
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

    return {"message": f"No orders were updated on WooCommerce."}
