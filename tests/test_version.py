# ## @DOC
# ### Test Version
# Tests if the project name in `pyproject.toml` matches "agent-dev-environment".



from pathlib import Path

import tomli


def test_version_matches():
    # Find pyproject.toml relative to this test
    path = Path(__file__).parent.parent / "pyproject.toml"
    with open(path, "rb") as f:
        data = tomli.load(f)
    assert data["project"]["name"] == "agent-dev-environment"
