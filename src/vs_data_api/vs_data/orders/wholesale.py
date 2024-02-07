import csv
import datetime
import os
from pathlib import Path

from vs_data_api.vs_data import log
from vs_data_api.vs_data.fm import db
from vs_data_api.vs_data.fm.constants import fname as _f
from vs_data_api.vs_data.fm.constants import tname as _t

CSV_EXPORT_DIR = os.environ.get("VSDATA_CSV_EXPORT_DIR", "tmp")

XERO_COLUMNS = {
    "x_contact_name": "*ContactName",
    "x_invoice_number": "*InvoiceNumber",
    "x_invoice_date": "*InvoiceDate",
    "x_invoice_due_date": "*DueDate",
    "description": "*Description",
    "quantity": "*Quantity",
    "unit_cost": "*UnitAmount",
    "account_code": "*AccountCode",
    "tax_rate": "*TaxType",
    # "exported": None,
}


def get_wholesale_orders(fmlinkdb):
    table = "link:xero_bacs_invoices"
    # vs_columns = (
    #     "x_contact_name",
    #     "x_invoice_number",
    #     "x_invoice_date",
    #     "x_invoice_due_date",
    #     "description",
    #     "quantity",
    #     "unit_cost",
    #     "account_code",
    #     "tax_rate",
    #     "exported",
    # )
    # xero_columns = (
    #     "*ContactName",
    #     "*InvoiceNumber",
    #     "*InvoiceDate",
    #     "*DueDate",
    #     "*Description",
    #     "*Quantity",
    #     "*UnitAmount",
    #     "*AccountCode",
    #     "*TaxType",
    #     # "Reference",
    # )
    exported = _f("link:xero_bacs_invoices", "exported")
    where = f"{exported}='no'"

    return db.select(fmlinkdb, table, XERO_COLUMNS.keys(), where=where)


def _unset_xero_exported_flag(connection, invoice_numbers: list):
    table_name = "link:xero_bacs_invoices"
    invoices = _t(table_name)
    exported = _f(table_name, "exported")
    x_invoice_number = _f(table_name, "x_invoice_number")
    sql = ""

    for xinv_id in invoice_numbers:
        sql = f"UPDATE {invoices} SET {exported}='yes' WHERE {x_invoice_number} = {xinv_id}"
        cursor = connection.cursor()
        log.info(sql)
        cursor.execute(sql)
        log.info(cursor.rowcount)
    connection.commit()


def export_wholesale_orders(fmlinkdb, order_id=None, cli: bool = False) -> list | None:
    if order_id:
        raise NotImplementedError()

    orders = get_wholesale_orders(fmlinkdb)
    # [{
    #     'x_contact_name': 'Fred Groom',
    #     'x_invoice_number': '72895',
    #     'x_invoice_date': datetime.date(2024, 1, 24),
    #     'x_invoice_due_date': datetime.date(2024, 1, 31),
    #     'description': 'Radish - French Breakfast 2(Organic)',
    #     'quantity': 1.0,
    #     'unit_cost': 2.05,
    #     'account_code': 201.0,
    #     'tax_rate': 'Zero Rated Income',
    #     'exported': 'no'
    # }]

    if orders:
        current_datetime = datetime.datetime.now()
        date_string = current_datetime.strftime("%Y-%m-%d_%H%M")
        csv_file_path = Path(CSV_EXPORT_DIR) / f"wholesale_orders_{date_string}.csv"
        field_names = list(XERO_COLUMNS.values())
        log.debug(csv_file_path)
        with open(csv_file_path, mode="w") as csv_file:
            csv_writer = csv.writer(csv_file, lineterminator="\n")
            csv_writer.writerow(field_names)
            for order in orders:
                order["x_invoice_due_date"] += datetime.timedelta(days=30)  # Add 30 days to x_invoice_due_date
                order["account_code"] = int(order["account_code"])  # Make account code a simple integer
                csv_writer.writerow(order.values())
        log.debug(orders)
        log.info(f"{len(orders)} orders exported to {csv_file_path}")
        exported_order_numbers = [int(order["x_invoice_number"]) for order in orders]
        _unset_xero_exported_flag(fmlinkdb, exported_order_numbers)
        return orders

    log.info("No orders to export")
    return False
