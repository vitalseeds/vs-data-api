"""Test cases for the __main__ module."""
import pytest
from vs_data.utils.fm import constants as fm_constants


def test_get_field_name():
    """Can get a field name string for a FileMaker table field"""

    assert fm_constants.fname("Acquisitions", "wp_product_id") == "wp_product_id"


def test_get_table_name():
    """Can get a table name string for a FileMaker table"""

    assert fm_constants.tname("Acquisitions") == "Acquisitions"
    assert fm_constants.tname("acquisitions") == "Acquisitions"
