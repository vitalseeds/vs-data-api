from typing import ClassVar

from . import FilemakerTable


class Products(FilemakerTable):
    table_name: ClassVar = "Products"

    SKU: str = "SKU"
    crop: str = "crop"
    link_wc_product_id: int = "_kf_WooCommerceID"
    sku: str = "SKU"
    name: str = "Name"
    # wc_product_id: str = "wc_product_id"


class ProductVariations(FilemakerTable):
    table_name: ClassVar = "ProductVariations"

    sku: str = "SKU"
    link_wc_variation_id: int = "_kf_WooCommerceID"
    variation_option: str = "ListProductAttributeOptions_c"
    # name: str = "Name"
    # wc_product_id: str = "wc_product_id"


class Orders(FilemakerTable):
    table_name: ClassVar = "Orders"

    link_wc_order_id: int = "_kf_WooCommerceID"
    status: str = "order_status"
    selected: str = "selected"  # Prevously select, which is q reserved word in SQL
    full_name: str = "BillingFullName_c"

    last_api_result: str = "LastAPIResult"
    date_completed_gmt: str = "DateCompletedGMT"
    date_completed: str = "DateCompleted"


class XeroBacsInvoices(FilemakerTable):
    table_name: ClassVar = "xero_bacs_invoices"

    x_contact_name: str = "X_contact_name"
    x_invoice_number: int = "X_invoice_number"
    x_invoice_date: str = "X_invoice_date"
    x_invoice_due_date: str = "X_invoice_due_date"
    description: str = "Description"
    quantity: int = "Quantity"
    unit_cost: float = "Unit cost"
    account_code: int = "Account code"
    tax_rate: float = "Tax Rate"
    exported: str = "exported"
