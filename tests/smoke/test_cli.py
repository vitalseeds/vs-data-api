"""
Smoke tests for the ``vs`` command line, with FileMaker and WooCommerce stubbed.

Each command is run with ``db.connection`` returning a fake connection and the
function it delegates to patched (``autospec`` so a call with the wrong
arguments fails). They check that the command starts, exits cleanly and passes
the right connection and options. The domain logic is covered elsewhere.
"""

import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch, sentinel

import pytest
from click.testing import CliRunner

from tests.fakes import FakeConnection
from vs_data_api import cli as vs

FMDB = "DSN=fm_cli"
LINKDB = "DSN=link_cli"
BASE_ARGS = ["--fmdb", FMDB, "--fmlinkdb", LINKDB]


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def connections():
    """Patch db.connection and get_api; returns {connection string: FakeConnection}."""
    opened = {}

    def fake_connection(connection_string):
        opened[connection_string] = FakeConnection(connect_string=connection_string)
        return opened[connection_string]

    with (
        patch.object(vs.db, "connection", side_effect=fake_connection),
        patch.object(vs.api, "get_api", return_value=sentinel.wcapi),
    ):
        yield opened


def run(runner, *args, **kwargs):
    result = runner.invoke(vs.cli, [*BASE_ARGS, *args], catch_exceptions=False, **kwargs)
    assert result.exit_code == 0, result.output
    return result


# command args, function the command delegates to, its return value
DELEGATING_COMMANDS = [
    (["update-stock"], "vs_data_api.vs_data.stock.update_wc_stock_for_new_batches", []),
    (["update-order-status", "--status", "processing"], "vs_data_api.vs_data.orders.update_packed_orders_status", []),
    (["apply-stock-corrections"], "vs_data_api.vs_data.stock.apply_corrections_to_wc_stock", []),
    (["push-variation-prices"], "vs_data_api.vs_data.products.price.push_variation_prices_to_wc", ([], None)),
    (["export-wholesale-orders", "--order-id", "5"], "vs_data_api.vs_data.orders.wholesale.export_wholesale_orders", []),
    (["stock-csv"], "vs_data_api.vs_data.stock.compare_wc_fm_stock", "report.csv"),
    (["get-wc-products", "1,2"], "vs_data_api.vs_data.stock.get_wc_products_by_id", []),
]

# Commands with their own tests below
OTHER_COMMANDS = {
    "update-stock-large-packets",
    "import-wc-product-ids",
    "get-wc-stock",
    "run-sql",
    "test-fm",
}


def test_help_lists_every_command(runner):
    result = runner.invoke(vs.cli, ["--help"])
    assert result.exit_code == 0
    for command in vs.cli.commands.values():
        assert command.name in result.output


def test_every_command_has_a_smoke_test():
    """Add new commands to DELEGATING_COMMANDS (or OTHER_COMMANDS) when they are created."""
    tested = {args[0] for args, *_ in DELEGATING_COMMANDS} | OTHER_COMMANDS
    assert set(vs.cli.commands) - tested == set()


@pytest.mark.parametrize("command", sorted(vs.cli.commands))
def test_command_help(runner, connections, command):
    # connections: the group connects to FileMaker even for a subcommand's --help
    result = runner.invoke(vs.cli, [command, "--help"])
    assert result.exit_code == 0, result.output


def test_isolate_does_not_connect(runner, connections):
    run(runner, "--isolate", "test-fm")
    assert connections == {}


@pytest.mark.parametrize("args, target, returns", DELEGATING_COMMANDS)
def test_command(runner, connections, args, target, returns):
    with patch(target, autospec=True, return_value=returns) as delegate:
        run(runner, *args)

    assert delegate.call_count == 1
    called_with = list(delegate.call_args.args) + list(delegate.call_args.kwargs.values())
    assert sentinel.wcapi in called_with or any(isinstance(arg, FakeConnection) for arg in called_with)


def test_update_order_status_passes_the_status(runner, connections):
    with patch("vs_data_api.vs_data.orders.update_packed_orders_status", autospec=True) as update:
        run(runner, "update-order-status", "--status", "processing")

    assert update.call_args.args[0] is connections[LINKDB]
    assert update.call_args.kwargs["target_status"] == "processing"


def test_export_wholesale_orders_uses_the_link_database(runner, connections):
    with patch("vs_data_api.vs_data.orders.wholesale.export_wholesale_orders", autospec=True) as export:
        run(runner, "export-wholesale-orders", "--order-id", "5")

    assert export.call_args.args[:2] == (connections[LINKDB], 5)


@pytest.mark.parametrize("answer, uploads", [("y\n", 1), ("n\n", 0)])
def test_update_stock_large_packets_asks_before_uploading(runner, connections, answer, uploads):
    with (
        patch("vs_data_api.vs_data.stock.get_large_batches_awaiting_upload_join_acq", return_value=[{"batch": 1}]),
        patch("vs_data_api.vs_data.stock.update_wc_stock_for_new_batches", autospec=True) as upload,
    ):
        run(runner, "update-stock-large-packets", input=answer)

    assert upload.call_count == uploads
    if uploads:
        assert upload.call_args.kwargs["product_variation"] == "large"


def test_update_stock_large_packets_force_skips_the_question(runner, connections):
    with (
        patch("vs_data_api.vs_data.stock.get_large_batches_awaiting_upload_join_acq", return_value=[{"batch": 1}]),
        patch("vs_data_api.vs_data.stock.update_wc_stock_for_new_batches", autospec=True) as upload,
    ):
        run(runner, "update-stock-large-packets", "--force", input="n\n")

    assert upload.call_count == 1


def test_import_wc_product_ids_copies_link_ids_into_vs_db(runner, connections):
    with (
        patch("vs_data_api.vs_data.stock.get_product_sku_map_from_linkdb", return_value=["sku map"]) as get_skus,
        patch("vs_data_api.vs_data.stock.get_product_variation_map_from_linkdb", return_value=["var map"]),
        patch("vs_data_api.vs_data.stock.update_acquisitions_wc_id") as update_ids,
        patch("vs_data_api.vs_data.stock.update_acquisitions_wc_variations") as update_variations,
    ):
        run(runner, "import-wc-product-ids")

    assert get_skus.call_args.args == (connections[LINKDB],)
    assert update_ids.call_args.args == (connections[FMDB], ["sku map"])
    assert update_variations.call_args.args == (connections[FMDB], ["var map"])


def test_get_wc_stock_looks_up_the_sku(runner, connections):
    with patch(
        "vs_data_api.vs_data.stock.get_wc_products_by_id", autospec=True, return_value=[{"id": 5, "stock_quantity": 3}]
    ) as get_products:
        connections_results = {"FROM ACQUISITIONS": [{"wc_product_id": 5, "wc_variation_lg_id": None}]}
        with patch.object(
            vs.db,
            "connection",
            side_effect=lambda cs: connections.setdefault(cs, FakeConnection(connections_results, cs)),
        ):
            run(runner, "get-wc-stock", "BeBO")

    assert "sku = 'BeBO'" in connections[FMDB].executed[0]
    assert get_products.call_args.args == (sentinel.wcapi, [5])


def test_run_sql_executes_on_the_main_database(runner, connections):
    run(runner, "run-sql", "UPDATE stock SET x = 1", "--commit")

    assert connections[FMDB].executed == ["UPDATE stock SET x = 1"]
    assert connections[FMDB].commits == 1


def test_run_sql_link_uses_the_link_database(runner, connections):
    run(runner, "run-sql", "SELECT 1", "--link", "--fetchall")

    assert connections[LINKDB].executed == ["SELECT 1"]


def test_test_fm(runner, connections):
    run(runner, "test-fm")
    run(runner, "test-fm", "--link")


@pytest.mark.parametrize("args", [["--help"], ["update-stock", "--help"]])
def test_help_works_without_settings(args):
    """No .env and no VSDATA_* variables, as on a fresh checkout."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("VSDATA_")}
    env["VSDATA_ENV_FILE"] = os.devnull + ".missing"
    result = subprocess.run(
        [sys.executable, "-c", "from vs_data_api.cli import cli; cli()", *args],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_command_help_does_not_connect(runner, connections):
    run(runner, "update-stock", "--help")
    assert connections == {}


def test_command_only_opens_the_connections_it_uses(runner, connections):
    with patch("vs_data_api.vs_data.orders.wholesale.export_wholesale_orders", autospec=True):
        run(runner, "export-wholesale-orders")

    assert list(connections) == [LINKDB]


def test_connections_default_to_settings(runner, connections):
    settings = SimpleNamespace(
        fm_connection_string="DSN=fm_settings",
        fm_link_connection_string="DSN=link_settings",
        vsdata_wc_url="https://wc.settings",
        vsdata_wc_key="ck",
        vsdata_wc_secret="cs",
    )
    with (
        patch.object(vs, "get_settings", return_value=settings),
        patch("vs_data_api.vs_data.stock.update_wc_stock_for_new_batches", autospec=True) as upload,
    ):
        result = runner.invoke(vs.cli, ["update-stock"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert upload.call_args.args == (connections["DSN=fm_settings"], sentinel.wcapi)
    vs.api.get_api.assert_called_once_with("https://wc.settings", "ck", "cs", check_status=False)
