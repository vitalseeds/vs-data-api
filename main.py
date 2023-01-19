
from functools import lru_cache

from fastapi import Depends, FastAPI


from vs_data.fm import db
from vs_data import stock
from vs_data import wc


import config

app = FastAPI()


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
async def get_product(product_id, settings: config.Settings = Depends(get_settings)):
    """
    Gets a product from the aquisitions table
    """
    return {"product": product_id}


@app.get("/batch/awaiting_upload")
async def get_product(settings: config.Settings = Depends(get_settings)):
    """
    Gets batches that are awaiting upload to store
    """

    cursor = db.connection(settings.fm_connection_string)
    batches = stock.get_batches_awaiting_upload(cursor)
    return {"batches": batches}


@app.get("/batch/upload-wc-stock")
async def upload_wc_stock(settings: config.Settings = Depends(get_settings)):
    """
    Increment stock for batches awaiting upload
    """
    connection = db.connection(settings.fm_connection_string)
    batches = stock.update_wc_stock_for_new_batches(connection, settings.wcapi)
    return {"batches": batches}
