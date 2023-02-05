"""Test cases for the __main__ module."""
import pytest
from vs_data import stock, log
from vs_data.fm import constants
import toml
import json
from rich import print

import responses
from responses import _recorder
from responses import matchers
import requests
from objexplore import explore

# import betamax
# CASSETTE_LIBRARY_DIR = "tests/fixtures/cassettes2"



# @pytest.mark.wcapi
# def test_get_products_by_id(wcapi):
#     product_ids = [5316, 1690, 1744, 1696, 10350]
#     products = stock.batch_upload.get_products_by_id(wcapi, product_ids)
#     # log.debug(products)
#     assert products



def flag_batches_for_upload(connection):
    fm_table = constants.tname("packeting_batches")
    awaiting_upload = constants.fname("packeting_batches", "awaiting_upload")
    batch_number = constants.fname("packeting_batches", "batch_number")
    sql = ""
    for batch in [3515, 3516, 3517]:
        sql = f"UPDATE {fm_table} SET {awaiting_upload}='Yes' WHERE {batch_number} = {batch}"
        cursor = connection.cursor()
        log.info(sql)
        cursor.execute(sql)
        log.info(cursor.rowcount)
    connection.commit()

# @responses._recorder.record(file_path="tests/fixtures/batch_awaiting_upload_wc_products.toml")
@responses.activate
def test_update_wc_stock_for_new_batches(wcapi, vsdb_connection, mocked_responses):
    flag_batches_for_upload(vsdb_connection)
    # responses.patch("http://vitalseedscouk.local/wp-json/wc/v3/products?include=28388.0%2C1716.0%2C10271.0")
    # responses.get("http://vitalseedscouk.local/wp-json/wc/v3/products")
    responses.get("http://vitalseedscouk.local")
    responses.patch("http://vitalseedscouk.local/wp-json/wc/v3/products/batch")
    responses._add_from_file(file_path="tests/fixtures/batch_awaiting_upload_wc_products.toml")
    stock.update_wc_stock_for_new_batches(vsdb_connection, wcapi)


def _add_from_file_params_from_url(responses, file_path: "Union[str, bytes, os.PathLike[Any]]", *args, **kwargs) -> None:
    """
    Replacement for responses.RequestsMock._add_from_file

    Allows for recorded responses to match subset of querystring params.
    Implemented to avoid failing match on generated oauth parameters.
    """
    # https://github.com/tombola/responses/blob/3b3ded7661fc3369431155baefb54975ceca5162/responses/__init__.py#L787
    try:
        import tomli as _toml
    except ImportError:
        # python 3.11
        import tomllib as _toml
    with open(file_path, "rb") as file:
        data = _toml.load(file)

    from urllib.parse import parse_qsl
    from urllib.parse import urlparse
    from urllib.parse import urlsplit, urlunsplit, urljoin
    # from requests.packages.urllib3.util.url import parse_url
    for rsp in data["responses"]:
        rsp = rsp["response"]

        request_url = urlparse(rsp["url"])
        request_query = request_url.query
        request_params = parse_qsl(request_query)

        # URL with the querystring removed
        request_url = urljoin(rsp["url"], request_url.path)

        print(f"[magenta]{request_url}")
        print(request_params)

        responses.add(
            method=rsp["method"],
            url=request_url,
            body=rsp["body"],
            # params=request_params,
            status=rsp["status"],
            content_type=rsp["content_type"],
            auto_calculate_content_length=rsp["auto_calculate_content_length"],
            **kwargs,
        )


# @responses._recorder.record(file_path="tests/fixtures/batch_awaiting_upload_wc_products.toml")
@responses.activate
def test_wcapi_stock(wcapi, vsdb_connection, mocked_responses):
    flag_batches_for_upload(vsdb_connection)

    expected_query_params = {"include": "28388.0,1716.0,10271.0"}
    # Allows WC GET request to match with a subset of parameters
    # File contains more than one request, fails for subsequent POST because
    # params do not match.
    _add_from_file_params_from_url(responses, file_path="tests/fixtures/batch_awaiting_upload_wc_products.toml",
        match=[
            matchers.query_param_matcher(expected_query_params, strict_match=False),
        ]
    )
    # responses._add_from_file(file_path="tests/fixtures/batch_awaiting_upload_wc_products.toml",
    #     match=[
    #         matchers.query_param_matcher(expected_query_params, strict_match=False),
    #     ]
    # )

    # Remove querystring matcher
    # responses.registered()[0].match = ()
    # explore(responses.registered())
    # responses.registered()[0]

    stock.update_wc_stock_for_new_batches(vsdb_connection, wcapi)


@responses.activate
def test_wcapi_request(wcapi, vsdb_connection, mocked_responses):
    flag_batches_for_upload(vsdb_connection)
    expected_query_params = {"include": "28388.0,1716.0,10271.0"}
    # expected_query_params = {"include": "28388.0,1716.0,10271.0"x, "something": "hello"}
    # responses._add_from_file(file_path="tests/fixtures/batch_awaiting_upload_wc_products.toml")
    # responses._add_from_file(file_path="tests/fixtures/batch_awaiting_upload_wc_products.toml",
    #     match=[
    #         matchers.query_param_matcher(expected_query_params, strict_match=False),
    #     ]
    # )
    _add_from_file_params_from_url(responses, file_path="tests/fixtures/batch_awaiting_upload_wc_products.toml",
        match=[
            matchers.query_param_matcher(expected_query_params, strict_match=False),
        ]
    )

    file_path="tests/fixtures/batch_awaiting_upload_wc_products.toml"


    requests.get("http://vitalseedscouk.local/wp-json/wc/v3/products?include=28388.0,1716.0,10271.0&per_page=100&oauth_consumer_key=ck_91b27f53dec56ef51dcd56cf2e63fe59364b04ba&oauth_timestamp=1675493888&oauth_nonce=5effb7db5b3468be2298bd560dc816378de9911a&oauth_signature_method=HMAC-SHA256&oauth_signature=A6NVF5g6NU5wqvAtrKBwqO3vasfpOBoW%2FswEbdYIO3M%3D&include=28388.0%2C1716.0%2C10271.0&per_page=100")




# def test_api(mocked_responses):
#     mocked_responses.get(
#         "http://twitter.com/api/1/foobar",
#         body="{}",
#         status=200,
#         content_type="application/json",
#     )
#     resp = requests.get("http://twitter.com/api/1/foobar")
#     assert resp.status_code == 200
