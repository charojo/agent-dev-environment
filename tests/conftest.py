# ## @DOC
# ### Conftest
# Configures pytest by adding a command-line option to preserve test projects and provides a fixture to check its value.



"""Pytest configuration for create-project tests."""

import pytest


def pytest_addoption(parser):
    """Add --keep option to preserve test projects."""
    parser.addoption(
        "--keep",
        action="store_true",
        default=False,
        help="Keep test projects after tests complete (don't cleanup)",
    )


@pytest.fixture
def keep_projects(request):
    """Check if --keep flag was passed."""
    return request.config.getoption("--keep")
