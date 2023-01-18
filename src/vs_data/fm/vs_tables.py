from . import FilemakerTable


class Acquisitions(FilemakerTable):
    table_name = "acquisitions"

    sku = "SKU"
    crop = "crop"
    wc_product_id = "wc_product_id"


class PacketingBatches(FilemakerTable):
    table_name = "packeting_batches"

    awaiting_upload = "awaiting_upload"
    sku = "sku"
    skufk = "skufk"
    batch_number = "batch_number"
    packets = "packets"
    to_pack = "to_pack"
