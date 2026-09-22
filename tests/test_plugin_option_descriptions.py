"""A plugin option's ``descriptionInUI`` reaches the settings page.

The loader built each option without reading it, so ten descriptions written for
the options page rendered nowhere.
"""

from __future__ import annotations

import json
from pathlib import Path

from game.plugins.luaplugin import LuaPluginDefinition
from tests.settings.test_settings_text import UK_SPELLING
from qt_ui.windows.settings.plugins import option_label_html

PLUGINS = Path("resources/plugins")


def test_every_written_option_description_is_loaded() -> None:
    checked = 0
    for manifest in sorted(PLUGINS.glob("*/plugin.json")):
        raw = json.loads(manifest.read_text(encoding="utf-8"))
        written = {
            option["mnemonic"]: option["descriptionInUI"]
            for option in raw.get("specificOptions") or []
            if option.get("descriptionInUI")
        }
        if not written:
            continue
        definition = LuaPluginDefinition.from_json(manifest.parent.name, manifest)
        loaded = {
            option.identifier.split(".", 1)[1]: option.description
            for option in definition.options
        }
        for mnemonic, description in written.items():
            assert loaded[mnemonic] == description, f"{manifest.parent.name}.{mnemonic}"
            checked += 1
    assert checked, "no plugin option carries a descriptionInUI any more"


def test_option_label_escapes_manifest_text() -> None:
    manifest = PLUGINS / "gpsjamming" / "plugin.json"
    definition = LuaPluginDefinition.from_json("gpsjamming", manifest)
    option = next(o for o in definition.options if o.description)
    option.name = "A & B <c>"
    label = option_label_html(option)
    assert label.startswith("<strong>A &amp; B &lt;c&gt;</strong><br />")


def test_plugin_text_is_us_english() -> None:
    offenders = []
    for manifest in sorted(PLUGINS.glob("*/plugin.json")):
        raw = json.loads(manifest.read_text(encoding="utf-8"))
        texts = [raw.get("nameInUI", ""), raw.get("descriptionInUI", "")]
        for option in raw.get("specificOptions") or []:
            texts += [option.get("nameInUI", ""), option.get("descriptionInUI", "")]
        offenders += [
            (manifest.parent.name, m.group(0))
            for text in texts
            if (m := UK_SPELLING.search(text))
        ]
    assert offenders == []
