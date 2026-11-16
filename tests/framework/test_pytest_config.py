import importlib.util
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).parents[2] / "pyproject.toml"


def test_xdist_is_installed():
    assert importlib.util.find_spec("xdist") is not None


def test_default_run_uses_four_workers():
    config = tomllib.loads(PYPROJECT.read_text("utf-8"))
    assert "-n 4" in config["tool"]["pytest"]["ini_options"]["addopts"]
