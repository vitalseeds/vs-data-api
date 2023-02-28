import click
from rich import print

@click.option("--large", is_flag=True)
@click.argument('sku')
@click.pass_context
def get_wc_stock(ctx, sku:str, large:bool=False):
    """
    Get WooCommerce stock value
    """
    if large:
        print("large stock count not implemented yet")
        return
    fmdb = ctx.parent.obj["fmdb"]
    wcapi = ctx.parent.obj["wcapi"]
    acquisitions = fmdb.cursor().execute(
        "SELECT wc_product_id, wc_variation_lg_id FROM ACQUISITIONS "
        f"WHERE wc_product_id IS NOT NULL AND sku = '{sku}'"
    ).fetchall()
    if not acquisitions:
        print("No acquisitions found")
        return
    product_ids = [p["wc_product_id"] for p in acquisitions]
    wc_products = stock.get_wc_products_by_id(wcapi, product_ids)
    wc_product_stock = {p["id"]:p["stock_quantity"] for p in wc_products}
    print(wc_product_stock)
