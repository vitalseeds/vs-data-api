from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import HTTPError, Timeout
from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
)
from woocommerce import API

from vs_data_api.vs_data import log

RETRY_ATTEMPTS = 3
# Replaced with a zero wait in tests
RETRY_WAIT = wait_exponential(multiplier=1, max=10)
# Server errors that are worth another go (a busy or restarting shop)
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
# Gateway errors and throttling are rejected before the request is processed,
# so they are safe to repeat even for POST
RETRY_STATUSES_POST = frozenset({429, 502, 503, 504})


def _log_retry(retry_state):
    outcome = retry_state.outcome
    reason = outcome.exception() if outcome.failed else f"HTTP {outcome.result().status_code}"
    log.warning(f"WooCommerce request failed ({reason}), retrying (attempt {retry_state.attempt_number})")


def _with_retries(call, exceptions, statuses):
    """
    Call `call()`, retrying on the given exceptions and response statuses.

    After the last attempt a bad response is returned, as without retries, so
    callers still decide what to do with it. An exception is raised.
    """
    return retry(
        retry=retry_if_exception_type(exceptions) | retry_if_result(lambda r: r.status_code in statuses),
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=RETRY_WAIT,
        before_sleep=_log_retry,
        retry_error_callback=lambda state: state.outcome.result(),
        reraise=True,
    )(call)()


class RetryingAPI(API):
    """
    The WooCommerce client, retrying dropped connections, timeouts and server errors.

    GET, PUT and DELETE are idempotent, so any of these are retried. POST is
    only retried when the request cannot have been processed (connection
    failure, not a read timeout), so a batch is never applied twice.
    """

    def get(self, endpoint, **kwargs):
        return _with_retries(
            lambda: super(RetryingAPI, self).get(endpoint, **kwargs), (RequestsConnectionError, Timeout), RETRY_STATUSES
        )

    def put(self, endpoint, data, **kwargs):
        return _with_retries(
            lambda: super(RetryingAPI, self).put(endpoint, data, **kwargs),
            (RequestsConnectionError, Timeout),
            RETRY_STATUSES,
        )

    def delete(self, endpoint, **kwargs):
        return _with_retries(
            lambda: super(RetryingAPI, self).delete(endpoint, **kwargs),
            (RequestsConnectionError, Timeout),
            RETRY_STATUSES,
        )

    def post(self, endpoint, data, **kwargs):
        return _with_retries(
            lambda: super(RetryingAPI, self).post(endpoint, data, **kwargs),
            RequestsConnectionError,
            RETRY_STATUSES_POST,
        )


def get_api(url, key, secret, check_status=False, verify_ssl=True):
    """
    Return a wcapi api instance (official simple wrapper library, with retries).

    If check_status then perform a test request first.
    """
    api = RetryingAPI(
        url=url,
        consumer_key=key,
        consumer_secret=secret,
        version="wc/v3",
        timeout=300,
        verify_ssl=verify_ssl,
    )
    if check_status:
        log.info(f"Testing WC API connection: {url}")
        try:
            api.get("/").raise_for_status()
        except HTTPError as msg:
            log.error(f"Could not access WooCommerce API ({url})")
            log.error(msg)
            return False

    return api
