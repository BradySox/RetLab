from qt_ui.softwarerender import (
    CHROMIUM_FLAGS_VAR,
    QUICK_BACKEND_VAR,
    apply_software_rendering,
    chromium_flags_value,
)


def test_flags_are_set_when_none_exist() -> None:
    assert chromium_flags_value(None) == "--disable-gpu --disable-gpu-compositing"
    assert chromium_flags_value("") == "--disable-gpu --disable-gpu-compositing"


def test_flags_append_to_the_users_own() -> None:
    assert (
        chromium_flags_value("--remote-debugging-port=9222")
        == "--remote-debugging-port=9222 --disable-gpu --disable-gpu-compositing"
    )


def test_flags_are_not_repeated() -> None:
    assert (
        chromium_flags_value("--disable-gpu --foo")
        == "--disable-gpu --foo --disable-gpu-compositing"
    )


def test_apply_sets_both_variables() -> None:
    env: dict[str, str] = {}
    apply_software_rendering(env)
    assert env[CHROMIUM_FLAGS_VAR] == "--disable-gpu --disable-gpu-compositing"
    assert env[QUICK_BACKEND_VAR] == "software"


def test_apply_keeps_a_users_quick_backend_and_flags() -> None:
    env = {CHROMIUM_FLAGS_VAR: "--foo", QUICK_BACKEND_VAR: "rhi"}
    apply_software_rendering(env)
    assert env[CHROMIUM_FLAGS_VAR] == "--foo --disable-gpu --disable-gpu-compositing"
    assert env[QUICK_BACKEND_VAR] == "rhi"
