from vs_data_api.vs_data import log, stock


def import_wc_product_ids_from_linkdb(vsdb, linkdb, cli=False):
    """
    Query the link db for wc product ids and add to the vs_db acquisitions table (based on sku)

    Args:
        FileMaker vsdb connection
        FileMaker linkdb connection

    """
    log.info("Updating product IDs from link database")

    # Get the WC:product_id for each SKU from the link database
    regular_product_skus = stock.get_product_sku_map_from_linkdb(linkdb)
    log.debug(regular_product_skus[:10])

    # Update acquisitions with wc_product_id
    stock.update_acquisitions_wc_id(vsdb, regular_product_skus)

    # Get the WC:variation_id for each SKU from the link database
    variations = stock.get_product_variation_map_from_linkdb(linkdb)
    log.debug(variations[:10])

    # Update acquisitions with WC variation ids for large and regular packets
    stock.update_acquisitions_wc_variations(vsdb, variations)

    return regular_product_skus, variations
