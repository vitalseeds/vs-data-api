"""Test suite for the vs_data package."""

import os
from typing import Any, Union
from urllib.parse import urljoin, urlparse

from responses import RequestsMock

try:
    import tomli as _toml  # noqa
except ImportError:
    # python 3.11
    import tomllib as _toml

from vs_data_api.vs_data.fm import constants


def _add_from_file_match_params(
    responses: RequestsMock, file_path: Union[str, bytes, os.PathLike[Any]], *args, **kwargs
) -> None:
    """
    Replacement for responses.RequestsMock._add_from_file

    Allows for recorded responses to match a subset of querystring params.
    Original provided by responses auto adds a full querystring matcher.
    Implemented to avoid failing match on generated oauth parameters.
    """

    with open(file_path, "rb") as file:
        data = _toml.load(file)

    for rsp in data["responses"]:
        rsp = rsp["response"]

        request_url = urlparse(rsp["url"])
        # Remove querystring so that responses does not add query_string_matcher:
        # https://github.com/getsentry/responses/blob/3b3ded7661fc3369431155baefb54975ceca5162/responses/__init__.py#L387
        request_url = urljoin(rsp["url"], request_url.path)
        print(f"{rsp['method']}: {request_url}")

        responses.add(
            method=rsp["method"],
            url=request_url,
            body=rsp["body"],
            status=rsp["status"],
            content_type=rsp["content_type"],
            auto_calculate_content_length=rsp["auto_calculate_content_length"],
            **kwargs,
        )


def flag_batches_for_upload(connection, batch_ids: list):
    fm_table = constants.tname("packeting_batches")
    awaiting_upload = constants.fname("packeting_batches", "awaiting_upload")
    batch_number = constants.fname("packeting_batches", "batch_number")
    sql = ""
    for batch in [3515, 3516, 3517]:
        sql = f"UPDATE {fm_table} SET {awaiting_upload}='Yes' WHERE {batch_number} = {batch}"
        cursor = connection.cursor()
        print(sql)
        cursor.execute(sql)
        print(cursor.rowcount)
    connection.commit()
