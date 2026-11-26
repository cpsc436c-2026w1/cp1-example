# From the B5T2 tutorial repository (tests/conftest.py), unchanged.
"""Tests write their simulated data sets into a temporary folder, never into sim/data/, so running the tests while
`uv run python -m sim.generate` or behave reads or writes sim/data/ cannot make either fail."""
import pytest

from sim import generate as g


@pytest.fixture(autouse=True, scope="session")
def _sim_data_in_a_temp_folder(tmp_path_factory):
    folder = tmp_path_factory.mktemp("sim-data")
    original = g.OUT
    g.OUT = folder
    yield folder
    g.OUT = original
