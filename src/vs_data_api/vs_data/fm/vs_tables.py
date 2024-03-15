from typing import ClassVar

from . import FilemakerTable


# TODO: classes should be pydantic models
class Acquisitions(FilemakerTable):
    table_name: ClassVar = "acquisitions"

    sku: str = "sku"
    crop: str = "crop"
    wc_product_id: int = "wc_product_id"
    wc_variation_lg_id: int = "wc_variation_lg_id"
    wc_variation_regular_id: int = "wc_variation_regular_id"
    not_selling_in_shop: str = "not_selling_in_shop"
    price: float = "Sale_price"
    lg_variation_price: float = "Large_price"
    packing_batch: int = "packing_batch"  # previously "Packing_batch"
    large_packing_batch: str = "Lrg_packing_batch"

    # foreign_table_name: {pk: "local_field_name", fk: "foreign_field_name"}
    # foreign_keys = {
    #     "packeting_batch": {"pk": "packing_batch", "fk": "batch_id"},
    # }


class PacketingBatches(FilemakerTable):
    table_name: ClassVar = "packeting_batches"

    awaiting_upload: str = "awaiting_upload"
    sku: str = "sku"
    skufk: str = "skufk"
    batch_number: int = "batch_number"
    packets: int = "packets"
    to_pack: int = "to_pack"
    pack_date: str = "pack_date"
    seed_lot: int = "seed_lot"  # previously SeedLotFK - change to number
    left_in_batch: int = "left_in_batch"


class LargeBatches(FilemakerTable):
    table_name: ClassVar = "large_batches"  # rename table occurence 'Growers_batches'

    awaiting_upload: str = "awaiting_upload"
    sku: str = "sku"  # previously SKUFK
    sku_variation: str = "sku_variation"  # previously SKU_var
    batch_number: int = "batch_number"
    packets: int = "packets"  # previously 'packed'
    to_pack: int = "to_pack"  # previously 'packets'
    pack_date: str = "pack_date"
    seed_lot: int = "seed_lot"  # previously SeedLotFK - change to number
    left_in_batch: int = "left_in_batch"  # previously 'Left in batch'


class SeedLots(FilemakerTable):
    table_name: ClassVar = "seed_lots"  # rename table occurence 'Growers_batches'

    lot_number: int = "lot_number"
    sku: str = "sku"  # previously 'SKUFK'


class Stock(FilemakerTable):
    table_name: ClassVar = "stock"

    sku: str = "sku"
    stock_large: int = "stock_large"
    stock_regular: int = "stock_regular"
    update: int = "update"
    update_large: int = "update_large"


class StockCorrections(FilemakerTable):
    table_name: ClassVar = "stock_corrections"

    id: int = "id"
    sku: str = "sku"
    large_packet_correction: int | None = "large_packet_correction"
    stock_change: int = "stock_change"
    wc_stock_updated: int | None = "wc_stock_updated"
    vs_stock_updated: int | None = "vs_stock_updated"
    create_line_item: int | None = "create_line_item"
    comment: str = "comment"


class LineItems(FilemakerTable):
    table_name: ClassVar = "LineItems_Orders"

    wc_order_id: int = "order_number"  # previously "Order number"
    sku: str = "SKU_fk"
    pack_size: str = "pack_size"  # previously "Pack_size"
    date: str = "date"  # previously "Date"
    # date_stamp: str = "date_stamp"  # previously "Date_stamp" (timsetamp automatically generated)
    quantity: int = "quantity"  # previously "Quantity"
    email: str = "email"
    item_cost: float = "item_cost"  # previously "Item cost"
    note: str = "note"  # previously "Note"
    correction_id: int = "correction_id"  # new field (number)
    stock_level: int = "stock_level"
    transaction_type: str = "transaction_type"  # previously 'Transaction_Type'
