from . import FilemakerTable


class Acquisitions(FilemakerTable):
    table_name = "acquisitions"

    sku = "SKU"
    crop = "crop"
    wc_product_id = "wc_product_id"
