import pytest


class RetryException(Exception): ...


# config
MAX_ATTEMPTS = 5
MIN_TIME = 0.1  # in seconds
MAX_TIME = 0.2  # in seconds

SHOW_EXCEPTIONS = False

pytest_plugins = ["pytester"]


@pytest.fixture
def disable_logging_exception(mocker):
    if not SHOW_EXCEPTIONS:
        mocker.patch("logging.exception", lambda *args, **kwargs: None)
