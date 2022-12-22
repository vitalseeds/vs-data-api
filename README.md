# VS-data API

Uses [Fast API][1] to provide a simple (documented) API for Vital Seeds data on
the local network.

The API is intended to be a **very** simple wrapper that delegates actual
business logic to a separate
dedicated python package ([vs-data][2]).

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



[1]: https://fastapi.tiangolo.com/
[2]: https://github.com/vitalseeds/vs-data