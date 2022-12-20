# VS-data API

Uses [Fast API][1] to provide a simple (documented) API for Vital Seeds data.

The API is intended to be a **very** simple wrapper that delegates actual
business logic to a separate
dedicated python package ([vs-data][2]).

Hopefully this will mean that
`vs-data-api` can be dedicated to providing endpoints, leaving the deep
FM integration (SQL queries etc) can be neatly encapsulated in `vs-data` and
more easily maintained, tested and extended.

[1]: https://fastapi.tiangolo.com/
[2]: https://github.com/vitalseeds/vs-data