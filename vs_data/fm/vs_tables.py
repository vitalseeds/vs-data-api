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


class PacketingBatches(FilemakerTable):
    table_name = "packeting_batches"

    awaiting_upload = "awaiting_upload"
    sku = "sku"
    skufk = "skufk"
    batch_number = "batch_number"
    packets = "packets"
    to_pack = "to_pack"
    pack_date = "pack_date"
    seed_lot = "seed_lot" # previously SeedLotFK - change to number


class LargeBatches(FilemakerTable):
    table_name = "large_batches"  # rename table occurence 'Growers_batches'

    awaiting_upload = "awaiting_upload"
    sku = "sku" # previously SKUFK
    sku_variation = "sku_variation"  # previously SKU_var
    batch_number = "batch_number"
    packets = "packets"  # previously 'packed'
    to_pack = "to_pack"  # previously 'packets'
    pack_date = "pack_date"
    seed_lot = "seed_lot"  # previously SeedLotFK - change to number


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
