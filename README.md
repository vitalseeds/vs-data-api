# VS-data API

Uses [Fast API][1] to provide a simple (documented) API for Vital Seeds data on
the local network.

The API is intended to be a **very** simple wrapper that delegates actual
business logic to a separate dedicated python package `vs-data`, now also in this repo.

Hopefully this will mean that
`vs-data-api` can be dedicated to providing endpoints, leaving the deep
FM integration (SQL queries etc) can be neatly encapsulated in `vs-data` and
more easily maintained, tested and extended.


## Basic usage

Run the FastAPI server:

```
uvicorn main:app --reload
```

Call the API from a FileMaker script:

```
#  Example call to vs-data-api (without arguments)
#  Set a valid vs-data-api endpoint (development server)
Set Variable [ $URL ; Value: "http://127.0.0.1:8000" ]

Insert from URL [ Select ; With dialog: On ; Target: $RESPONSE ; $URL ]

Set Variable [ $MESSAGE ; Value: JSONGetElement ( $RESPONSE ; "message" ) ]

# Show the response
Show Custom Dialog [ $URL ; $MESSAGE ]
```

🎉 Should show a dialog with the message `VS Data API running` (returned from root
endpoint)

# VS-data

*Previously its own [installable package][2], now moved into the this repo to allow simpler maintenance.*

This is a python library that serves as a bridge between inventory management in
FileMaker, and order details on vitalseeds.co.uk.

Aims to replace opaque and proprietary FM 'scripts' - specifically where they
interact with the WooCommerce/WP website.


## Requirements

To connect to Filemaker:

- filemaker database
- fm user configured with `all access`
- ODBC manager installed and configured with a DSN for the db (optional, can
  connect direct)
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
  - make use of robust third party libraries such as [WooCommerce][3]
  - be version controlled
  - use automated testing
  - be edited and searched as text, ie with a full featured code editor like [VScode](https://code.visualstudio.com/)
  - be **much** more performant
  - be iterated and improved more simply


[1]: https://fastapi.tiangolo.com/
[2]: https://github.com/vitalseeds/vs-data
[3]: https://pypi.org/project/WooCommerce/
[wcapi]: https://woocommerce.com/document/woocommerce-rest-api/#section-2