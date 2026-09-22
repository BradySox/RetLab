"""The settings dialog is a published page. Pins the text classes the 2026-09-22
consistency audit fixed, so a layout move or a feature removal cannot quietly
make a description wrong again."""

from __future__ import annotations

import re
from collections.abc import Iterator

from game.settings import ChoicesOption, OptionDescription, Settings
from tools.audit_stale_docs import REMOVED

#: Tags the dialog's rich-text label renders as intended. Anything else vanishes:
#: "PUSH <word>" displayed as "PUSH ".
ALLOWED_TAGS = re.compile(r"</?(?:br|strong|b|i|em)\s*/?>")

#: UI text is US English (2026-09-22 DM call). Field names keep their spelling.
UK_SPELLING = re.compile(
    r"(?:behaviour|defence|armour|theatre|modell(?:ed|ing)|flavour|colour|centre"
    r"|prioritis|customis|unrefuelled|metres?)",
    re.IGNORECASE,
)

#: A description may NAME another setting, never point at it by position: the
#: layout table moves fields between sections and pages without touching text.
#: The RetLab Features page lift left four such pointers aimed at nothing.
POSITIONAL = re.compile(
    r"\b(?:settings?|sliders?|factors?|cap|defaults?|options?) (?:above|below)\b"
    r"|\b(?:the|use the) above\b",
    re.IGNORECASE,
)


def _options() -> Iterator[tuple[str, str, str, OptionDescription]]:
    for page in Settings.pages():
        for section in Settings.sections(page):
            for name, description in Settings.fields(page, section):
                yield page, section, name, description


def _texts(description: OptionDescription) -> Iterator[str]:
    yield description.text
    if description.detail:
        yield description.detail
    if description.tooltip:
        yield description.tooltip
    if isinstance(description, ChoicesOption):
        yield from description.choices


def test_no_setting_hides_its_explanation_behind_hover() -> None:
    # DM rule 2026-07-20: a description renders in full; nothing is hover-only.
    assert [name for *_, name, d in _options() if d.tooltip] == []


def test_nautical_miles_are_written_nm() -> None:
    offenders = [
        name for *_, name, d in _options() if re.search(r"\((?:nm|nmi)\)", d.text)
    ]
    assert offenders == []


def test_no_setting_describes_a_removed_feature_as_live() -> None:
    # The published-docs table, applied to the dialog: a feature removal adds
    # one Removed row and every surface is guarded by it.
    offenders = []
    for *_, name, description in _options():
        for text in _texts(description):
            for entry in REMOVED:
                match = re.search(entry.pattern, text)
                if match and not any(t in text for t in entry.allowed):
                    offenders.append((name, entry.what, match.group(0)))
    assert offenders == []


def test_setting_text_survives_the_rich_text_label() -> None:
    offenders = []
    for *_, name, description in _options():
        for text in (description.text, description.detail or ""):
            stray = ALLOWED_TAGS.sub("", text)
            if "\n" in text or "`" in text or "&#" in text or re.search(r"<\w", stray):
                offenders.append(name)
    assert offenders == []


def test_descriptions_name_other_settings_rather_than_pointing() -> None:
    offenders = [
        (name, match.group(0))
        for *_, name, d in _options()
        for text in _texts(d)
        if (match := POSITIONAL.search(text))
    ]
    assert offenders == []


def test_section_names_are_sentence_case() -> None:
    offenders = []
    for page in Settings.pages():
        for section in Settings.sections(page):
            words = re.findall(r"[A-Za-z][\w-]*", section)[1:]
            if any(w[0].isupper() and not w.isupper() for w in words):
                offenders.append(f"{page} / {section}")
    assert offenders == []


def test_setting_text_is_us_english() -> None:
    offenders = [
        (name, match.group(0))
        for *_, name, d in _options()
        for text in _texts(d)
        if (match := UK_SPELLING.search(text))
    ]
    offenders += [
        (page, section)
        for page in Settings.pages()
        for section in Settings.sections(page)
        if UK_SPELLING.search(section)
    ]
    assert offenders == []
