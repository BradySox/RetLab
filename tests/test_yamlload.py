from pathlib import Path

import yaml

from game import yamlload
from game.yamlload import safe_load_yaml


def test_uses_the_c_parser_when_pyyaml_has_it() -> None:
    if yaml.__with_libyaml__:
        assert yamlload._Loader is yaml.CSafeLoader


def test_matches_safe_load_on_shipped_campaigns() -> None:
    campaigns = sorted(Path("resources/campaigns").glob("*.yaml"))
    assert campaigns
    for path in campaigns:
        text = path.read_text(encoding="utf-8")
        assert safe_load_yaml(text) == yaml.safe_load(text), path.name


def test_refuses_python_tags_like_safe_load() -> None:
    try:
        safe_load_yaml("!!python/object/apply:os.system ['echo']")
    except yaml.constructor.ConstructorError:
        return
    raise AssertionError("loaded a python tag")
