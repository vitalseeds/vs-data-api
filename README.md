# VS-data

This is a python library that serves as a bridge between inventory management in
FileMaker, and order details on vitalseeds.co.uk.

Aims to replace opaque and proprietary FM 'scripts' - specifically where they
interact with the WooCommerce/WP website.


## Requirements

To connect to Filemaker:

- filemaker database
- fm user configured with `all access`
- ODBC manager instaleld and configured with a DSN for the db
- Filemaker ODBC driver

To connect to WooCommerce:

- [API credentials][wcapi]


## Installation

- `pip install ...(TBC)`
- Set environment variables (these can also be passed as arguments eg when calling from FM)
  - `VSDATA_FM_CONNECTION_STRING`
  - `VSDATA_WC_URL`
  - `VSDATA_WC_KEY`
  - `VSDATA_WC_SECRET`

## Rationale

- FM scripts
  - are quite error prone
  - almost impossible to test and debug
  - have extremely poor documentation
  - have very limited and costly external support
- python scripts can
  - make use of robust third party libraries such as [WooCommerce][1]
  - be version controlled
  - use automated testing
  - be edited and searched as text, ie with a full featured code editor like [VScode](https://code.visualstudio.com/)
  - be **much** more performant
  - be iterated and improved more simply

[1]: https://pypi.org/project/WooCommerce/
[wcapi]: https://woocommerce.com/document/woocommerce-rest-api/#section-2