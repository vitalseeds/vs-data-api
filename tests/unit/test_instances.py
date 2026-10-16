"""The debugger (#118) must be able to tell when more than one copy of the API is running.

Two instances (e.g. the standalone service and a developer copy) fight over the
same port and the same FileMaker connection, so we detect them by the port they listen on.
"""

import socket

import pytest

from vs_data_api.instances import check_single_instance, is_port_listening


@pytest.fixture
def listener():
    """A real listening socket, standing in for a running API instance."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    yield sock.getsockname()[1]
    sock.close()


@pytest.fixture
def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_port_with_a_listener_is_reported_as_listening(listener):
    assert is_port_listening(listener) is True


def test_unused_port_is_not_reported_as_listening(free_port):
    assert is_port_listening(free_port) is False


def test_no_instance_running_is_ok_to_start(free_port):
    result = check_single_instance(free_port)
    assert result["ok"] is True


def test_instance_already_running_blocks_a_second_one(listener):
    result = check_single_instance(listener)
    assert result["ok"] is False
    assert str(listener) in result["error"]
