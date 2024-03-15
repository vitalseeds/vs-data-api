"""Test cases for the __main__ module."""
import pytest
from pypika import Order, Query, Tables

# from objexplore import explore

from tests import flag_only_test_batches_for_upload
from vs_data_api.vs_data import log, stock
from vs_data_api.vs_data.factories import create_batch_for_upload, create_test_acquisition

TEST_BATCH_ID = 99999


def get_test_batch(vsdb_connection, batch_number=TEST_BATCH_ID):
    # awaiting = _f("packeting_batches", "awaiting_upload")
    # # where = f"lower({awaiting})='yes' AND b.pack_date IS NOT NULL"
    # where = f"lower({awaiting})='yes' AND B.batch_number = {batch_number}"
    # where = f"lower({awaiting})='yes' AND B.sku = 'TEST_SKU'"

    # sql = (
    #     "SELECT B.awaiting_upload,B.batch_number, B.packets, A.sku, A.wc_product_id  "
    #     'FROM "packeting_batches" B '
    #     'LEFT JOIN "acquisitions" A ON B.sku = A.SKU '
    #     f"WHERE {where} "
    #     "ORDER BY B.batch_number DESC "
    #     # "FETCH FIRST 10 ROWS ONLY "
    # )
    # log.debug(sql)

    packeting_batches, acquisitions = Tables("packeting_batches", "acquisitions")
    sql = (
        Query.from_("packeting_batches")
        .select("awaiting_upload", "batch_number", "packets")
        .where(packeting_batches.awaiting_upload == "yes")
        .where(packeting_batches.batch_number == batch_number)
        .orderby("batch_number", order=Order.desc)
    )

    rows = vsdb_connection.cursor().execute(sql.get_sql()).fetchall()
    log.info(rows)
    return rows


def delete_test_batch(vsdb_connection, batch_number):
    sql = f'DELETE FROM "packeting_batches" WHERE batch_number = {batch_number} '
    log.debug(sql)
    vsdb_connection.cursor().execute(sql).commit()


def delete_test_acquisition(vsdb_connection, sku):
    sql = f"DELETE FROM \"acquisitions\" WHERE sku = '{sku}'"
    log.debug(sql)
    vsdb_connection.cursor().execute(sql).commit()


@pytest.mark.fmdb
def test_get_batches_awaiting_upload_join_acq(vsdb_connection):
    delete_test_batch(vsdb_connection, TEST_BATCH_ID)
    delete_test_acquisition(vsdb_connection, "TEST_SKU")

    create_test_acquisition(vsdb_connection)
    create_batch_for_upload(vsdb_connection, TEST_BATCH_ID)

    test_batch = get_test_batch(vsdb_connection, TEST_BATCH_ID)
    assert test_batch
    assert len(test_batch) == 1
    log.info(test_batch)

    flag_only_test_batches_for_upload(vsdb_connection, [TEST_BATCH_ID])

    batches = stock.batch_upload.get_batches_awaiting_upload_join_acq(vsdb_connection)
    assert batches
    assert len(batches) == 1


@pytest.mark.wcapi
def test_get_products_by_id(wcapi):
    product_ids = [5316, 1690, 1744, 1696, 10350]
    products = stock.batch_upload.get_wc_products_by_id(wcapi, product_ids)
    assert products
