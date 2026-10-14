from unittest.mock import MagicMock, patch

from vs_data_api.vs_data.stock import batch_upload

MODULE = "vs_data_api.vs_data.stock.batch_upload"


def _batch(number, sku, product_id, variation_id, packets=10):
    return {
        "awaiting_upload": "yes",
        "batch_number": number,
        "packets": packets,
        "sku": sku,
        "wc_product_id": product_id,
        "wc_variation_lg_id": variation_id,
    }


def _wcapi():
    wcapi = MagicMock()
    get_response = MagicMock(status_code=200)
    get_response.json.return_value = {"stock_quantity": 5}
    wcapi.get.return_value = get_response
    put_response = MagicMock()
    put_response.json.return_value = {"id": 28733}
    wcapi.put.return_value = put_response
    return wcapi


def test_large_batch_without_wc_ids_is_skipped():
    """A batch whose sku has no WC product/variation ids must not break the upload."""
    batches = [
        _batch("GR1824", "OnWl", 1691, 28733),
        _batch("GR1829", "SPGW", None, None),
    ]
    wcapi = _wcapi()

    with (
        patch(f"{MODULE}.get_large_batches_awaiting_upload_join_acq", return_value=batches),
        patch(f"{MODULE}._unset_awaiting_upload_flag") as unset_flag,
    ):
        batch_upload.update_wc_stock_for_new_batches(MagicMock(), wcapi, "large")

    # only the batch with WC ids is uploaded and unflagged
    assert unset_flag.call_args.args[1] == ["GR1824"]
    wcapi.put.assert_called_once_with("products/1691/variations/28733", {"stock_quantity": 15})


def test_only_batches_without_wc_ids_does_nothing():
    batches = [_batch("GR1829", "SPGW", None, None)]
    wcapi = _wcapi()

    with (
        patch(f"{MODULE}.get_large_batches_awaiting_upload_join_acq", return_value=batches),
        patch(f"{MODULE}._unset_awaiting_upload_flag") as unset_flag,
    ):
        result = batch_upload.update_wc_stock_for_new_batches(MagicMock(), wcapi, "large")

    assert result is False
    wcapi.get.assert_not_called()
    unset_flag.assert_not_called()
