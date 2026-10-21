"""Telling the map and the open My aircraft window that a saved point changed (§102).

Ported from juanjux/dcs-escalation (LGPL-3.0).
"""

from game.server import EventStream
from game.sim import GameUpdateEvents


def publish_points_changed() -> None:
    EventStream.put_nowait(GameUpdateEvents(saved_points_updated=True))
    # Imported here: the server package must load without the Qt windows.
    from qt_ui.windows.GameUpdateSignal import GameUpdateSignal

    signal = GameUpdateSignal.get_instance()
    if signal is not None:
        # The routes run on the web server's thread, not Qt's.
        signal.notify_saved_points_changed()
