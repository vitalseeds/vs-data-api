from . import FilemakerTable


class Acquisitions(FilemakerTable):
    table_name = "acquisitions"

    sku = "sku"
    crop = "crop"
    wc_product_id = "wc_product_id"
    wc_variation_lg_id = "wc_variation_lg_id"
    wc_variation_regular_id = "wc_variation_regular_id"
    not_selling_in_shop = "not_selling_in_shop"
    price = "Sale_price"
    lg_variation_price = "Large_price"
    packing_batch = "packing_batch"  # previously "Packing_batch"
    large_packing_batch = "Lrg_packing_batch"

    # foreign_table_name: {pk: "local_field_name", fk: "foreign_field_name"}
    # foreign_keys = {
    #     "packeting_batch": {"pk": "packing_batch", "fk": "batch_id"},
    # }


class PacketingBatches(FilemakerTable):
    table_name = "packeting_batches"

    awaiting_upload = "awaiting_upload"
    sku = "sku"
    skufk = "skufk"
    batch_number = "batch_number"
    packets = "packets"
    to_pack = "to_pack"
    pack_date = "pack_date"
    seed_lot = "seed_lot"  # previously SeedLotFK - change to number
    left_in_batch = "left_in_batch"


class LargeBatches(FilemakerTable):
    table_name = "large_batches"  # rename table occurence 'Growers_batches'

    awaiting_upload = "awaiting_upload"
    sku = "sku"  # previously SKUFK
    sku_variation = "sku_variation"  # previously SKU_var
    batch_number = "batch_number"
    packets = "packets"  # previously 'packed'
    to_pack = "to_pack"  # previously 'packets'
    pack_date = "pack_date"
    seed_lot = "seed_lot"  # previously SeedLotFK - change to number
    left_in_batch = "left_in_batch"  # previously 'Left in batch'


class SeedLots(FilemakerTable):
    table_name = "seed_lots"  # rename table occurence 'Growers_batches'

    lot_number = "lot_number"
    sku = "sku"  # previously 'SKUFK'


class Stock(FilemakerTable):
    table_name = "stock"

    sku = "sku"
    stock_large = "stock_large"
    stock_regular = "stock_regular"
    update = "update"
    update_large = "update_large"


class StockCorrections(FilemakerTable):
    table_name = "stock_corrections"

    id = "id"
    sku = "sku"
    large_packet_correction = "large_packet_correction"
    stock_change = "stock_change"
    wc_stock_updated = "wc_stock_updated"
    vs_stock_updated = "vs_stock_updated"
    comment = "comment"


class LineItems():
    table_name = "LineItems_Orders"

    wc_order_id = "order_number"  # previously "Order number"
    sku = "SKU_fk"
    pack_size = "pack_size"  # previously "Pack_size"
    date = "date"  # previously "Date"
    # date_stamp = "date_stamp"  # previously "Date_stamp" (timsetamp automatically generated)
    quantity = "quantity"  # previously "Quantity"
    email = "email"
    item_cost = "item_cost"  # previously "Item cost"
    note = "note"  # previously "Note"
    correction_id = "correction_id"  # new field (number)