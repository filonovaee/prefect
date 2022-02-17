import asyncio
import logging
import pathlib
import warnings

import pytest

# Initialize logging
import prefect

from .fixtures.api import *
from .fixtures.client import *
from .fixtures.database import *
from .fixtures.logging import *

profile = prefect.context.get_profile_context()
profile.initialize()


def pytest_addoption(parser):
    parser.addoption(
        "--service",
        action="append",
        metavar="SERVICE",
        default=[],
        help="include service integration tests for SERVICE.",
    )
    parser.addoption(
        "--only-service",
        action="append",
        metavar="SERVICE",
        default=[],
        help="exclude all tests except service integration tests for SERVICE.",
    )
    parser.addoption(
        "--all-services",
        action="store_true",
        default=False,
        help="include all service integration tests",
    )


def pytest_collection_modifyitems(session, config, items):
    """
    Modify all tests to automatically and transparently support asyncio
    """
    if config.getoption("--all-services"):
        # Do not skip any service tests
        return

    only_services = set(config.getoption("--only-service"))
    if only_services:
        only_running_blurb = f"Only running tests for service(s): {', '.join(repr(s) for s in only_services)}."
        for item in items:
            item_services = {mark.args[0] for mark in item.iter_markers(name="service")}
            not_in_only_services = only_services.difference(item_services)
            if not_in_only_services:
                item.add_marker(pytest.mark.skip(only_running_blurb))

        if config.getoption("--service"):
            warnings.warn(
                "`--only-service` cannot be used with `--service`. `--service` will be ignored."
            )
        return

    run_services = set(config.getoption("--service"))
    for item in items:
        item_services = {mark.args[0] for mark in item.iter_markers(name="service")}
        missing_services = item_services.difference(run_services)
        if missing_services:
            item.add_marker(
                pytest.mark.skip(
                    f"Requires service(s): {', '.join(repr(s) for s in missing_services)}. "
                    "Use '--service NAME' to include."
                )
            )


@pytest.fixture(scope="session")
def event_loop(request):
    """
    Redefine the event loop to support session/module-scoped fixtures;
    see https://github.com/pytest-dev/pytest-asyncio/issues/68
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()

    # configure asyncio logging to capture long running tasks
    asyncio_logger = logging.getLogger("asyncio")
    asyncio_logger.setLevel("WARNING")
    asyncio_logger.addHandler(logging.StreamHandler())
    loop.set_debug(True)
    loop.slow_callback_duration = 0.25

    try:
        yield loop
    finally:
        loop.close()

    # Workaround for failures in pytest_asyncio 0.17;
    # see https://github.com/pytest-dev/pytest-asyncio/issues/257
    policy.set_event_loop(loop)


@pytest.fixture
def tests_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent
