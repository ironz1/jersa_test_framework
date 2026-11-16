import importlib.util
import shlex
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).parents[2] / "pyproject.toml"


def test_xdist_is_installed():
    assert importlib.util.find_spec("xdist") is not None


def test_default_run_uses_four_workers():
    config = tomllib.loads(PYPROJECT.read_text("utf-8"))
    tokens = shlex.split(config["tool"]["pytest"]["ini_options"]["addopts"])
    worker_values = [tokens[i + 1] for i, token in enumerate(tokens[:-1]) if token == "-n"]
    assert worker_values == ["4"]
