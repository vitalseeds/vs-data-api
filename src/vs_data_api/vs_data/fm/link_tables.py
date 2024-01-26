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


class Orders(FilemakerTable):
    table_name = "Orders"

    link_wc_order_id = "_kf_WooCommerceID"
    status = "order_status"
    selected = "selected"  # Prevously select, which is q reserved word in SQL
    full_name = "BillingFullName_c"

    last_api_result = "LastAPIResult"
    date_completed_gmt = "DateCompletedGMT"
    date_completed = "DateCompleted"


class XeroBacsInvoices(FilemakerTable):
    table_name = "xero_bacs_invoices"

    x_contact_name = "X_contact_name"
    x_invoice_number = "X_invoice_number"
    x_invoice_date = "X_invoice_date"
    x_invoice_due_date = "X_invoice_due_date"
    description = "Description"
    quantity = "Quantity"
    unit_cost = "Unit cost"
    account_code = "Account code"
    tax_rate = "Tax Rate"
    exported = "exported"
