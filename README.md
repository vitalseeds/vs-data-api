# VS-data API

Uses [Fast API][1] to provide a simple (documented) API for Vital Seeds data on
the local network.

The API is intended to be a **very** simple wrapper that delegates actual
business logic to a separate dedicated python package `vs-data`, now also in this repo.

Hopefully this will mean that
`vs-data-api` can be dedicated to providing endpoints, leaving the deep
FM integration (SQL queries etc) can be neatly encapsulated in `vs-data` and
more easily maintained, tested and extended.

## How development is set up

Development uses a Windows VM (Vagrant + VirtualBox) that has FileMaker Pro and
the FileMaker ODBC driver installed. **The API runs inside the VM**, so it talks
to FileMaker over ODBC on the VM's own `localhost` and no ODBC traffic crosses
the host/VM boundary. The code is edited on the Mac, through a shared folder.

```
 Mac (host)                                   Windows VM (windows10-vm)
 ───────────────────────────────              ──────────────────────────────────────
 VS Code ── edits files ──► vs-data-api/ ═══► C:\vagrant\vs-data-api   (shared folder)
                                                     │ run by service vs_data_api
 browser / curl / FileMaker ─► 127.0.0.1:8080 ══► uvicorn :8000 ──ODBC──► FileMaker Pro
                                                                      localhost:2399
```

- **Host to VM API:** `http://127.0.0.1:8080/` (the VM's port 8000, forwarded).
  Interactive docs are at <http://127.0.0.1:8080/docs>.
- **Code:** the clone in the VM folder, `windows10-vm/vs-data-api`, is what the
  service runs. Edit that folder on the Mac, not another clone elsewhere.
- **Not supported:** connecting the host's Python straight to the VM's FileMaker
  over the forwarded ODBC port (`2399`) was tried and fails with `Failed to
  connect to listener (3)`. This is why the API runs inside the VM, next to
  FileMaker.

### Why a VM, and not FileMaker on the Mac?

The production database is built on **FileMaker 18**. Running it locally used to
be the normal way to develop (`Server=localhost`), but on current macOS this no
longer works:

- FileMaker Pro 18 is not compatible with recent versions of macOS (the
  development Mac now runs macOS 26). Claris only supports each FileMaker
  release on a limited range of macOS versions, and 18 has fallen out of it.
- On the newer macOS, FileMaker's **ODBC/JDBC sharing is broken**: the
  `fmxdbc_listener` and the FileMaker ODBC driver can no longer be relied on
  to connect. Without ODBC sharing there is no way for vs-data to read or write
  the database, so the API cannot run on the Mac against a local FileMaker.
- The VM runs Windows 10, which FileMaker Pro 18 does support, so ODBC sharing
  works there, and the API can reach it on the VM's own `localhost`.

(The observation that ODBC sharing breaks on the newer macOS is from
hands-on use rather than from Claris documentation, check the
[Claris compatibility list](https://www.claris.com/resources/compatibility/) for
the exact supported macOS versions. FileMaker Pro 18 and the ODBC driver still
install and open files on the Mac, the failure is at the ODBC/sharing layer.)

Practical consequences:

- Run and develop against the VM, as in the [Quick start](#quick-start-vm).
- Do not expect `Server=localhost` strings in `.envrc` or `.env.example` to
  work on a current Mac. They are only valid **inside** the VM (or on a Mac
  with an older macOS that FileMaker 18 supports).
- Upgrading FileMaker to a version supported on the current macOS would let you
  run locally again, but is a separate (licensing and compatibility) decision.

If you do have a supported combination of FileMaker and macOS, see
[Running locally without the VM](#running-locally-without-the-vm).

## Quick start (VM)

### One-off setup

1. **Requirements on the Mac**
   - [VirtualBox](https://www.virtualbox.org/wiki/Downloads) and
     [Vagrant](https://developer.hashicorp.com/vagrant/downloads)
   - the FileMaker Pro 18 installer (`filemaker_pro_18/Setup.exe` and
     `Assisted Install.txt` with the licence key) in the VM folder's
     `vagrant/resources`
   - the [FileMaker ODBC driver](https://support.claris.com/s/article/Software-Update-FileMaker-xDBC-client-drivers-for-FileMaker-1503692806454)
     installer (matching your FileMaker version) in `vagrant/resources`
   - [Windows App](https://apps.apple.com/us/app/windows-app/id1295203466)
     (remote desktop) for `vagrant rdp`
   - this repo cloned **inside** the VM folder: `windows10-vm/vs-data-api`
2. **Build the VM**

   ```sh
   cd ~/vitalseeds/windows10-vm
   vagrant up
   vagrant rdp          # opens the Windows desktop
   ```

3. **Finish what is not yet automated** (in the VM desktop)
   - open FileMaker Pro once and enter the licence
   - run the 64 bit ODBC driver installer
4. **Open the database in FileMaker and enable ODBC** (see
   [Enabling ODBC in FileMaker](#enabling-odbc-in-filemaker)). The dev database
   is `test_vs_db.fmp12`, in the shared folder as `C:\vagrant\test_vs_db.fmp12`.
5. **Give the service its configuration.** Copy `.env.example` to `.env` in
   the repo folder (so `windows10-vm/vs-data-api/.env` on the Mac, which is
   `C:\vagrant\vs-data-api\.env` in the VM) and fill in the five variables from
   [Configuration](#configuration). Example (note: `Server=localhost`, as the
   API runs *inside* the VM; quotes are optional and are stripped):

   ```
   VSDATA_FM_CONNECTION_STRING="Driver={FileMaker ODBC};Server=localhost;Database=test_vs_db;UID=vsdata;PWD=<password>"
   VSDATA_FM_LINK_CONNECTION_STRING="Driver={FileMaker ODBC};Server=localhost;Database=test_link_db;UID=vsdata;PWD=<password>;"
   VSDATA_WC_URL="http://vitalseeds.local"
   VSDATA_WC_KEY="<key>"
   VSDATA_WC_SECRET="<secret>"
   ```

   The app loads this file itself at start-up, so the service needs **no**
   environment of its own. If the service was previously configured with
   `nssm edit`, clear that, because real environment variables take precedence
   over `.env`:

   ```powershell
   nssm reset vs_data_api AppEnvironmentExtra
   ```

6. **Start the service and check it**

   ```sh
   # in the VM
   nssm restart vs_data_api
   # on the Mac
   curl http://127.0.0.1:8080/         # {"message": "VS Data API running"}
   curl http://127.0.0.1:8080/health   # FileMaker (main + link db) and WooCommerce
   ```

   `/health` returns `200` with `"status": "ok"` when everything is reachable,
   or `503` and `"status": "degraded"` with the failing check and its error
   (no credentials are included). It is the quickest way to see *which* part of
   the setup is wrong.

### Day to day

1. `vagrant up` (the service starts with Windows; it is delayed-auto-start, so
   give it a minute).
2. In FileMaker in the VM, open the database(s) (ODBC is only served for open
   files).
3. Edit code on the Mac in `windows10-vm/vs-data-api`. The service runs
   uvicorn with `--reload`, so code changes are picked up automatically.
4. Browse <http://127.0.0.1:8080/docs>, or call the endpoints from FileMaker.
5. After changing `.env` or **dependencies**, restart the service:
   `nssm restart vs_data_api` (`.env` is only read at start, `--reload` only
   watches code files).

Useful tasks from the Mac, in this repo (the `Makefile` expects the VM folder
at `../windows10-vm`; override with `VM_DIR=...`):

```sh
make help         # list all tasks
make vm-up        # vagrant up
make vm-status    # VM and service state
make vm-restart   # nssm restart vs_data_api (after changing .env or dependencies)
make vm-logs      # tail the uvicorn log in the VM (LOG_LINES=100 for more)
make vm-health    # call /health, exits non-zero if degraded
```

Logs are in `C:\logs\` in the VM.

## Configuration

Settings come from environment variables, which are loaded at start-up (by
`src/vs_data_api/env.py`) from a **`.env` file** in the repo root, or from the
file named by `VSDATA_ENV_FILE`. Real environment variables (direnv, your shell,
a service manager) always take precedence over the file. `.env` is gitignored;
`.env.example` is the template.

Quotes around values are optional and are stripped, and an `export ` prefix is
allowed, so `.env` and a direnv `.envrc` can share content. (This is not true of
`nssm edit`, which keeps quotes as part of the value; that is why the service
should read `.env` rather than have its own environment.)

**All five of these are required**; the server and the `vs` command will not
start without them (with a validation error listing the missing ones).

| Variable | Example |
|---|---|
| `VSDATA_FM_CONNECTION_STRING` | `Driver={FileMaker ODBC};Server=localhost;Database=<db>;UID=<user>;PWD=<password>` |
| `VSDATA_FM_LINK_CONNECTION_STRING` | as above, for the link database |
| `VSDATA_WC_URL` | `https://example.com` |
| `VSDATA_WC_KEY` | WooCommerce API consumer key ([how to create][wcapi]) |
| `VSDATA_WC_SECRET` | WooCommerce API consumer secret |

Optional: `VSDATA_TMP_DIR`, `VSDATA_CSV_EXPORT_DIR`, `AUDIT_LOG_DIR`,
`VS_DATA_LOGGING_LEVEL`. See `.env.example`.

Connection strings can be a DSN (`DSN=name;UID=...;PWD=...`) instead, but it must
be a **system** DSN in the **64 bit** ODBC manager
(`C:\Windows\System32\odbcad32.exe`) and must itself name the database.
A DSN-less string with `Database=` is simpler.

### Enabling ODBC in FileMaker

In FileMaker (Pro or Server) for each database vs-data connects to (the main db
and the link db):

1. `File > Manage > Security`: create an account for vs-data (eg `vsdata`) with
   a privilege set that has the `fmxdbc` extended privilege (`Allow ODBC/JDBC`).
2. `File > Sharing > Enable ODBC/JDBC...`: set to **On**, and allow that
   privilege set (or "All users"). The menu item only appears in Layout mode.
3. FileMaker Pro only serves ODBC for files that are **currently open**, and
   `Database=` in the connection string must match the open file's name (without
   `.fmp12`).
4. Passwords are always checked, "All users" only controls which privilege sets
   may use ODBC.

## Calling the API from FileMaker

Call the API from a FileMaker script:

```
#  Example call to vs-data-api (without arguments)
#  Set a valid vs-data-api endpoint (development server)
#  FileMaker on the Mac: 8080 (forwarded). FileMaker inside the VM: 8000
Set Variable [ $URL ; Value: "http://127.0.0.1:8080" ]

Insert from URL [ Select ; With dialog: On ; Target: $RESPONSE ; $URL ]

Set Variable [ $MESSAGE ; Value: JSONGetElement ( $RESPONSE ; "message" ) ]

# Show the response
Show Custom Dialog [ $URL ; $MESSAGE ]
```

🎉 Should show a dialog with the message `VS Data API running` (returned from root
endpoint)

### Setup in FileMaker

Filemaker can trigger actions by requesting fastapi endpoints.

Filemaker does not support import/export of scripts, so you will need to set
these up yourself. See the `fm_scripts` directory for examples.

## Running locally without the VM

This only works if your FileMaker and macOS versions are a supported combination
with working ODBC sharing (see [Why a VM, and not FileMaker on the
Mac?](#why-a-vm-and-not-filemaker-on-the-mac)): FileMaker Pro 18 on a current
macOS does not. If it does work for you, you can run the API directly, with
[uv](https://docs.astral.sh/uv/) (installs Python 3.11 and the dependencies):

1. Prerequisites: the FileMaker ODBC driver, and on macOS `brew install
   libiodbc` (make sure `unixodbc` is **not** installed).
2. `uv sync`
3. Put the five [variables](#configuration) in `.env` (loaded automatically)
   with `Server=localhost` and your local database name. Variables already
   exported in the shell (for example by [direnv](https://direnv.net/) from an
   `.envrc`) win over `.env`; restart `uvicorn` after changing either.
4. Check the connection: `uv run vs test-fm`
5. Run the API:

   ```sh
   uv run uvicorn src.vs_data_api.main:app --reload
   curl http://127.0.0.1:8000/
   ```

   This is port **8000** (docs at `/docs`), not 8080, which is the VM's.

### The `vs` CLI

```sh
uv run vs --help        # list available commands
uv run vs test-fm       # check the FileMaker connection
uv run vs <command>
```

or activate the virtual environment (`source .venv/bin/activate`) so `vs` is on
your PATH, or call `.venv/bin/vs`. With pip, run `pip install -e .` in your own
virtual environment. The CLI needs the same environment variables as the server.

To run a command against a different settings file:

```sh
VSDATA_ENV_FILE=.env-test uv run vs import-wc-product-ids
```

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Not sure what is wrong | `make vm-health` (or `curl http://127.0.0.1:8080/health`): shows which of FileMaker, the link db and WooCommerce fails, and why |
| `curl http://127.0.0.1:8080/` hangs or no response | VM not running, or the service is stopped: `vagrant up`, then `nssm start vs_data_api`, check `C:\logs\vs_data_api_err.log` |
| `IM002 Data source name not found and no default driver specified` | the DSN does not exist as a **system, 64 bit** DSN, or (commonly) a value is **quoted** in the NSSM environment, because NSSM keeps quotes as part of the value. Put the settings in `.env` instead and run `nssm reset vs_data_api AppEnvironmentExtra` |
| `Failed to connect to listener (2)` | nothing listening: FileMaker not running in the VM, ODBC sharing off, or wrong host/port |
| `Failed to connect to listener (3)` | something answered but rejected the session: the database is not open, ODBC sharing is not enabled for it, or the connection is coming from outside the VM (host to VM ODBC is not supported, use the API on 8080) |
| `ValidationError ... Field required` on start or any `vs` command | one of the five required variables is not set for that process |
| Changed `.env`, behaviour unchanged | the process keeps what it read at start: `nssm restart vs_data_api` (or restart `uvicorn` locally). Also check a stale NSSM environment or shell variable is not overriding the file: real environment variables win |
| Code changes do not show up | the service must be running the clone you are editing (`windows10-vm/vs-data-api`). `--reload` on a shared folder can miss file changes; `nssm restart vs_data_api` |
| New dependency missing in the VM | the service uses the VM's global Python: `pip install ...` (or `pip install -e .`) in the VM, then restart |
| `Can't open lib 'FileMaker ODBC' : file not found` or a `unixodbc` warning (Mac) | `brew uninstall unixodbc && brew install libiodbc`, reinstall the FileMaker ODBC driver |
| `TypeError: Client.__init__() got an unexpected keyword argument 'app'` in tests | `httpx` >= 0.28 with the pinned starlette. The `test` extra now pins `httpx<0.28`; re-run `uv sync --extra test` |

## Standalone Deployment

For production use, VS Data API can be packaged as a standalone executable and run as a system service. This allows the API to:

- Start automatically on boot
- Run without a Python environment
- Be accessible across your local network

See **[README_standalone_build.md](README_standalone_build.md)** for complete instructions on:
- Building executables for macOS and Windows

See **[README_standalone_install.md](README_standalone_install.md)** for complete instructions on:
- Installing and configuring as a system service
- Network configuration and firewall setup
- Testing and troubleshooting

## Tests

Tests use pytest. The default run needs no FileMaker, WooCommerce or
credentials (dummy settings are filled in by `tests/conftest.py`), so it can be
run at any time:

```sh
uv sync --extra test
make test                             # everything that runs without external systems
make smoke                            # just the smoke tests
make cov                              # with a coverage report
uv run pytest --fmdb --wcapi         # also end to end, against FileMaker and WooCommerce
```

| Folder | What it covers |
|---|---|
| `tests/smoke/` | Every API endpoint and `vs` command starts and calls the right thing. New endpoints and commands must be added here (a test fails otherwise) |
| `tests/unit/` | Complex logic: stock corrections, batch upload, order status, variation prices |
| `tests/integration/wc/` | WooCommerce order calls against a local site (marked `wcapi`, skipped by default; no FileMaker needed) |
| `tests/integration/fm/` | End to end against a real FileMaker database and WooCommerce site (marked `fmdb` / `wcapi`, skipped by default) |

FileMaker is replaced by `tests/fakes.py:FakeConnection`, which records SQL and
returns canned rows. WooCommerce is the real client with HTTP intercepted by
[`responses`](https://github.com/getsentry/responses), so no request leaves the
machine.

End-to-end tests (`fmdb`, `wcapi`) use the `VSDATA_TEST_*` settings from the
environment or `.env`. They connect to a real FileMaker database and
WooCommerce site, so point these at **test** copies, never production.
FileMaker ODBC only works inside the Windows VM, so run them there.

### WooCommerce tests against LocalWP

`make test-wc` runs the order tests in `tests/integration/wc/` against the
site in `VSDATA_TEST_WC_*` (a LocalWP site such as `http://vitalseeds.local`
with a read/write REST key and permalinks other than "Plain"). It runs on the
Mac with no VM. Each test creates its own throw-away order and deletes it, and
every test is skipped unless the host is `localhost`, `127.0.0.1`, `::1` or `*.local`/`*.localhost` (set
`VSDATA_TEST_WC_ALLOW_REMOTE=1` to use another site such as staging).

To check HPOS (#116), run it once with HPOS off, switch HPOS on in
WooCommerce > Settings > Advanced > Features, and run it again. The output
prints `HPOS enabled: True/False`.

`tests/integration/fm_mock/` (SQLite over ODBC in place of FileMaker) is
switched off and needs the [sqliteodbc driver](http://www.ch-werner.de/sqliteodbc/).

### Checks before committing

`make lint` checks code complexity (ruff) and scans for committed secrets
(gitleaks). To run the same checks on every commit:

```sh
uv run --extra dev pre-commit install
```

CI runs the tests and these checks on every pull request
(`.github/workflows/test.yml`).

# VS-data

_Previously its own [installable package][2], now moved into the this repo to allow simpler maintenance._

This is a python package that serves as a bridge between inventory management in
FileMaker, and order details on vitalseeds.co.uk.

Aims to replace opaque and proprietary FM 'scripts' - specifically where they
interact with the WooCommerce/WP website.

## Rationale

- FM scripts
  - are quite error prone
  - almost impossible to test and debug
  - have extremely poor documentation
  - have very limited and costly external support
- python scripts can
  - make use of robust third party libraries such as [WooCommerce][3]
  - be version controlled\
  - use automated testing
  - be edited and searched as text, ie with a full featured code editor like [VScode](https://code.visualstudio.com/)
  - be **much** more performant
  - be iterated and improved more simply

[1]: https://fastapi.tiangolo.com/
[2]: https://github.com/vitalseeds/vs-data
[3]: https://pypi.org/project/WooCommerce/
[wcapi]: https://woocommerce.com/document/woocommerce-rest-api/#section-2
