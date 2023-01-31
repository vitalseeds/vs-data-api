from . import FilemakerTable


class Products(FilemakerTable):
    table_name = "Products"

    SKU = "SKU"
    crop = "crop"
    link_wc_product_id = "_kf_WooCommerceID"
    sku = "SKU"
    name = "Name"
    # wc_product_id = "wc_product_id"

class ProductVariations(FilemakerTable):
    table_name = "ProductVariations"

    sku = "SKU"
    link_wc_variation_id = "_kf_WooCommerceID"
    variation_option = "ListProductAttributeOptions_c"
    # name = "Name"
    # wc_product_id = "wc_product_id"
