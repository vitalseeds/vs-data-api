from datetime import datetime


from vs_data_api.vs_data import log
from vs_data_api.vs_data.fm import db
from vs_data_api.vs_data.fm.constants import fname as _f
from vs_data_api.vs_data.fm.constants import tname as _t
from vs_data_api.vs_data.stock.misc import WC_MAX_API_RESULT_COUNT, batched

LAST_BATCH_UPDATE_LOG = "tmp/orders_batch_update_response.json"
LOG_HINT = r"Details are in C:\Program Files\VSData\logs\stderr.log"


class OrderUpdateFailed(Exception):
    """
    Orders could not be (fully) updated on WooCommerce.

    The message is written for office staff and shown in FileMaker; technical
    detail goes to the log. ``updated`` holds any orders that did succeed.
    """

    def __init__(self, message: str, updated: list | None = None):
        super().__init__(message)
        self.updated = updated or []


def _wc_rejection_message(status_code: int) -> str:
    if status_code in (401, 403):
        reason = "WooCommerce refused the update (a login or permissions problem)."
    else:
        reason = "WooCommerce couldn't process the update right now."
    return f"{reason} Nothing was changed on the website. Try again shortly, or ask IT to check the log. {LOG_HINT}"


def get_selected_orders(fmlinkdb):
    table = "link:orders"
    columns = ["link_wc_order_id", "full_name", "status", "selected"]
    selected = _f("link:orders", "selected")
    # order_status = _f("link:orders", "status")
    where = (
        f"lower({selected})='yes' "
        # f"AND lower({order_status})='{status}'"
    )
    where = (
        # Using lower() appears to be slow
        f"{selected}='yes' OR {selected}='Yes' "
    )
    # where = (
    #     f"{selected}='Yes' "
    #     f"AND {order_status}='{status}'"
    # )
    return db.select(fmlinkdb, table, columns, where=where)


def _same_status(a: str, b: str) -> bool:
    return a.removeprefix("wc-") == b.removeprefix("wc-")


def _post_order_batch(wcapi, orders: list, target_status: str) -> list:
    order_updates = [{"id": order["link_wc_order_id"], "status": target_status} for order in orders]
    data = {"update": order_updates}
    log.debug(data)
    response = wcapi.post("orders/batch", data)

    if response.status_code != 200:
        log.error(f"WooCommerce orders/batch returned {response.status_code}: {response.text[:500]}")
        raise OrderUpdateFailed(_wc_rejection_message(response.status_code))

    updates = []
    for u in response.json().get("update", []):
        if u.get("error"):
            log.error(f"WooCommerce could not update order {u.get('id')}: {u['error']}")
        elif not _same_status(u.get("status", ""), target_status):
            log.error(f"WooCommerce left order {u.get('id')} as '{u.get('status')}', not '{target_status}'")
        else:
            # Reduce log noise by picking out pertinent details
            updates.append(
                {
                    "id": u.get("id", ""),  # 46015
                    "order_key": u.get("order_key", ""),  # wc_order_12345abcdef
                    "status": u.get("status", ""),  # "completed"
                    "date_completed": u.get("date_completed", ""),  # "2023-02-14T13:47:24"
                    "date_completed_gmt": u.get("date_completed_gmt", ""),  # "2023-02-14T13:47:24"
                }
            )
    return updates


def wc_orders_update_status(wcapi, orders: list, target_status: str) -> list:
    """
    Post status changes to WooCommerce in batches, returning the orders it confirmed.

    Only orders WooCommerce reports with the target status count as updated. If a
    batch fails outright, OrderUpdateFailed is raised carrying the orders confirmed
    by earlier batches in ``updated``.
    """
    confirmed = []
    for batch in batched(orders, WC_MAX_API_RESULT_COUNT):
        try:
            confirmed.extend(_post_order_batch(wcapi, list(batch), target_status))
        except OrderUpdateFailed as e:
            e.updated = confirmed
            raise
    return confirmed


def _fm_completion_date_or_now(date: str | None):
    if not date:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Filemaker does not acknowledge timezone
    return date.replace("T", " ")


def link_db_update_completed_orders(fmlinkdb: object, wc_updated_orders: list) -> int:
    orders_table = _t("link:orders")

    link_wc_order_id = _f("link:orders", "link_wc_order_id")
    status = _f("link:orders", "status")
    selected = _f("link:orders", "selected")
    # last_api_result = _f("link:orders", "last_api_result")
    date_completed_gmt = _f("link:orders", "date_completed_gmt")
    date_completed = _f("link:orders", "date_completed")

    rows_affected = 0
    for order in wc_updated_orders:
        completion_date = _fm_completion_date_or_now(order.get("date_completed", None))
        sql = (
            f'UPDATE "{orders_table}" '
            f"SET {status}='{order['status']}', "
            f"{selected}='', "
            # f"{last_api_result}='{update_response}', "
            f"{date_completed}=TIMESTAMP '{completion_date}', "
            f"{date_completed_gmt}=TIMESTAMP '{completion_date}' "
            f'WHERE "{link_wc_order_id}" = {order["id"]}'
        )
        log.debug(sql)
        cursor = fmlinkdb.cursor()
        cursor.execute(sql)
        rows_affected += cursor.rowcount
        fmlinkdb.commit()

    log.debug(f"{rows_affected=}")
    return rows_affected


def link_db_set_status_for_orders(fmlinkdb: object, wc_updated_orders: list, target_status: str) -> int:
    """Set the status and clear the selection of just the orders WooCommerce confirmed."""
    orders_table = _t("link:orders")
    link_wc_order_id = _f("link:orders", "link_wc_order_id")
    selected = _f("link:orders", "selected")
    status = _f("link:orders", "status")

    rows_affected = 0
    for order in wc_updated_orders:
        sql = (
            f'UPDATE "{orders_table}" '
            f"SET {selected}='', {status}='{target_status}' "
            f'WHERE "{link_wc_order_id}" = {order["id"]}'
        )
        log.debug(sql)
        cursor = fmlinkdb.cursor()
        cursor.execute(sql)
        rows_affected += cursor.rowcount
        fmlinkdb.commit()

    log.debug(f"{rows_affected=}")
    return rows_affected


def update_packed_orders_status(fmlinkdb, wcapi, cli: bool = False, target_status: str = "completed") -> list:
    # Assume for now that we only want to get orders that are in 'packing'
    orders = get_selected_orders(fmlinkdb)
    # orders = [{'link_wc_order_id': 46011, 'full_name': 'Roberta Mathieson', 'status': 'packing', 'selected': 'Yes'}]
    log.debug(f"{len(orders)=}")

    if not orders:
        log.warning("No orders are selected in the link database, so nothing was sent to WooCommerce")
        raise OrderUpdateFailed(
            "No orders were sent to WooCommerce because none are selected. Select the orders and try again."
        )

    failure = None
    try:
        wc_updates = wc_orders_update_status(wcapi, orders, target_status=target_status)
    except OrderUpdateFailed as e:
        failure, wc_updates = e, e.updated
    log.info(f"WooCommerce confirmed {len(wc_updates)} of {len(orders)} orders")
    log.debug(wc_updates)

    if wc_updates:
        if target_status == "completed":
            link_result = link_db_update_completed_orders(fmlinkdb, wc_updates)
            log.info(f"Link database orders marked 'completed': {link_result} rows affected")
        else:
            link_db_set_status_for_orders(fmlinkdb, wc_updates, target_status)

    updated_ids = {u["id"] for u in wc_updates}
    failed_ids = [o["link_wc_order_id"] for o in orders if o["link_wc_order_id"] not in updated_ids]
    if not failed_ids:
        return wc_updates

    log.warning(f"Orders left selected in the link database: {failed_ids}")
    if not wc_updates:
        if failure:
            raise failure
        raise OrderUpdateFailed(f"WooCommerce didn't update any orders. Ask IT to check the log. {LOG_HINT}")
    raise OrderUpdateFailed(
        f"{len(wc_updates)} of {len(orders)} orders were updated. "
        f"These couldn't be updated and are still selected: {', '.join(str(i) for i in failed_ids)}. {LOG_HINT}",
        updated=wc_updates,
    )
