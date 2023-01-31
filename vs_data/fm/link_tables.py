from . import FilemakerTable


class Products(FilemakerTable):
    table_name = "Products"

    SKU = "SKU"
    crop = "crop"
    link_wc_product_id = "_kf_WooCommerceID"
    sku = "SKU"
    name = "Name"
    # wc_product_id = "wc_product_id"
