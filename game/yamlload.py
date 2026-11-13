"""YAML reading through libyaml's C parser when it is installed.

PyYAML's pure-Python parser is about six times slower; RetLab reads some 2,600
YAML files (campaigns, units, factions), and the New Game window alone parses
every campaign. The C loader returns the same data; PyYAML ships it in its wheels.
"""

from __future__ import annotations

from typing import IO, Any, Union

import yaml

try:
    _Loader: Any = yaml.CSafeLoader
except AttributeError:  # PyYAML built without libyaml
    _Loader = yaml.SafeLoader


def safe_load_yaml(stream: Union[str, bytes, IO[str], IO[bytes]]) -> Any:
    """``yaml.safe_load`` with the C parser when available."""
    return yaml.load(stream, Loader=_Loader)
