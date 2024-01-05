# FileMaker scripts

Actions performed in python are called from filemaker via http request to
fastapi endpoints.

FileMaker doesn't allow for exporting/importing scripts, but the basics are
replicated\* here for reference.

Basically we

1. Run a `GLOBALS` script on opening the FileMaker 'file' (database) in
order to expose some constants for the endpoint paths. This means they can be
changed if necessary without hunting down the paths in FM scripts.
2. Access endpoints by passing the path to `VSDATA` function, so that FileMaker
   HTP request handling can be encapsulated there.

---

\* _by 'printing' scripts to PDF and then copy paste_ 🤦‍♂️