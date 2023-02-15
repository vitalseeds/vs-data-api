from vs_data.stock.misc import get_all_products, get_all_wc_products
from vs_data.stock.batch_upload import get_wc_large_variations_by_product
from vs_data.cli.table import display_product_table, display_table
import json
import pandas as pd
import pickle
from os.path import exists
import os
from vs_data.fm.db import convert_pyodbc_cursor_results_to_lists
from vs_data.fm import db
from vs_data.fm.constants import fname as _f
from vs_data.fm.constants import tname as _t
from vs_data import log
from rich import print
import numpy as np
from datascroller import scroll

from datetime import datetime

LAST_BATCH_UPDATE_LOG = "tmp/orders_batch_update_response.json"


def get_selected_orders(fmlinkdb):
    table = "link:orders"
    columns = ["link_wc_order_id", "full_name", "status", "selected"]
    selected = _f("link:orders", "selected")
    # order_status = _f("link:orders", "status")
    where = (
        f"lower({selected})='yes' "
        # f"AND lower({order_status})='{status}'"
    )
    # where = (
    #     f"{selected}='Yes' "
    #     f"AND {order_status}='{status}'"
    # )
    return db.select(fmlinkdb, table, columns, where=where)


def wc_orders_update_status(wcapi, orders:dict[dict], status:str):
    order_updates = []
    for order in orders:
        order_updates.append(
            {
                "id": order["link_wc_order_id"],
                "status": status,
            }
        )
    data = {"update": order_updates}
    log.debug(data)
    response = wcapi.post("orders/batch", data).json()
    
    # Reduce noise by picking out pertinent details
    updates = [
        {
            "id": u["id"], # 46015
            "order_key": u["order_key"], # wc_order_12345abcdef
            "status": u["status"], # "completed"
            "date_completed": u["date_completed"], # "2023-02-14T13:47:24"
            "date_completed_gmt": u["date_completed_gmt"], # "2023-02-14T13:47:24"
        }
        for u in response.get("update")
    ]
    edited_response = {"update": updates}
    with open(LAST_BATCH_UPDATE_LOG, "w") as file:
        json.dump(edited_response, file, indent=2)
    # with open("tmp/orders_batch_update_response_FULL.json", "w") as file:
    #     json.dump(response, file, indent=2)
    return edited_response


def link_db_update_orders(fmlinkdb: object, update_response: dict):
    wc_updated_orders = update_response["update"]
    orders_table = _t("link:orders")

    link_wc_order_id = _f("link:orders", "link_wc_order_id")
    status = _f("link:orders", "status")
    selected = _f("link:orders", "selected")
    last_api_result = _f("link:orders", "last_api_result")
    date_completed_gmt = _f("link:orders", "date_completed_gmt")
    date_completed = _f("link:orders", "date_completed")

    rows_affected = 0
    for order in wc_updated_orders:
        completion_date = order.get('date_completed', None)
        if not completion_date:
            completion_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        sql = (
            f'UPDATE "{orders_table}" '
            f"SET {status}='{order['status']}', "
            f"{selected}='No', "
            # f"{last_api_result}='{update_response}', "
            f"{date_completed}=TIMESTAMP '{completion_date}', "
            f"{date_completed_gmt}=TIMESTAMP '{completion_date}' "
            f'WHERE "{link_wc_order_id}" = {order["id"]}'
        )
        log.debug(sql)
        cursor = fmlinkdb.cursor()
        cursor.execute(sql)
        # log.debug(f"{cursor.rowcount=}")
        rows_affected += cursor.rowcount
        fmlinkdb.commit()

    log.debug(f"{rows_affected=}")
    return rows_affected


def update_packed_orders_status(fmlinkdb, wcapi, cli: bool=False, status="completed"):
    # Assume for now that we only want to get orders that are in 'packing'
    orders = get_selected_orders(fmlinkdb)
    # orders = [{'link_wc_order_id': 46011, 'full_name': 'Roberta Mathieson', 'status': 'packing', 'selected': 'Yes'}]
    log.debug(orders)

    if orders:
        wc_response = wc_orders_update_status(wcapi, orders, status=status)
        log.info("WooCommerce updated")
        log.debug(wc_response)
        # TODO - only update link db if target status was 'completed'
        link_result = link_db_update_orders(fmlinkdb, wc_response)
        log.info(f"Link database updated: {link_result} rows affected")

        return wc_response.get("update", [])
