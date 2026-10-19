# vs_doctor (vsdata-doctor)

A first-line debugger for office staff, shipped as `vsdata-doctor.exe` on each
release. It must always run, so it never imports `vs_data_api` (a test enforces
this). Spec: docs/superpowers/specs/2026-10-15-vsdata-doctor-design.md (#118).

Keep it simple: one job per module (config, windows, diagnose, fixes, checks,
runner, report, gui, __main__). `gui.py` is the Tkinter window (sv-ttk theme);
`__main__` falls back to the rich console flow if the window can't start or
breaks. `--console` forces the console, `--selftest` opens and closes the window
(used by CI), `--no-pause` affects only the console. Spec:
docs/superpowers/specs/2026-10-17-vsdata-doctor-friendly-ui-design.md (#131). Deeper logic goes in `diagnose.py` or `fixes.py`, not in
`checks.py`.

## Surface area: what the doctor relies on

If you change any of these in the app, update the doctor (and this list) in the
same change.

| What | Defined in the app | Used by |
|---|---|---|
| Developer settings: `.env` found as in `vs_data_api.env` (`VSDATA_ENV_FILE`, repo root, cwd), used only when there is no config.ini; `VSDATA_<KEY>` for the `[vsdata]` keys, `VSDATA_PORT`, and doctor-only `VSDATA_DOCTOR_<KEY>` | `vs_data_api.env`, `.env.example` | `config.py`, `checks.check_config` |
| Config file location | `vs_data_api.config.get_config_dir` (copied; parity test) | `config.py` |
| `[vsdata]` keys `fm_connection_string`, `fm_link_connection_string`, `wc_url`, `wc_key`, `wc_secret`, optional `wc_verify_ssl` (default true) | `config/config.ini.example`, `vs_data_api.config.load_ini_config` | `config.py`, `checks.py` |
| `[server] port` (default 8432) | `vs_data_api.standalone` | `checks.check_server_health` |
| `GET /health`: 200 ok or 503 degraded, body `{"status", "checks": {"filemaker", "filemaker_link", "woocommerce": {"ok", "error"}}}` | `vs_data_api.health.run_checks`, `main.get_health` (contract test) | `diagnose.get_health`, `diagnose.explain_health` |
| http or https on localhost (https when certificates exist) | `vs_data_api.standalone.get_ssl_paths` | `diagnose.get_health` |
| Service name `VSDataAPI` | `deploy/windows/install-service.ps1`, `update.ps1` | `[doctor] service_name` default, `windows.service_state` |
| Log file `C:\Program Files\VSData\logs\stderr.log` | `deploy/windows/install-service.ps1` (NSSM `AppStderr`) | `[doctor] log_file` default |
| WooCommerce REST: `GET /wp-json/wc/v3/products` with basic auth | `vs_data_api.vs_data.wc` | `diagnose.try_website` |
| FileMaker process name starts with `FileMaker`; ODBC error texts | FileMaker Pro and its ODBC driver | `windows.filemaker_running`, `diagnose.explain_odbc_error` |
| Release asset `vsdata-doctor.exe` | `.github/workflows/build.yml`, `vsdata-doctor.spec` | — |
| Tk and `sv-ttk` bundled in that exe (`sv-ttk` in the `dev` extra, its data files collected in the spec) | `pyproject.toml`, `vsdata-doctor.spec`, the CI `--selftest` step | `gui.py` |
