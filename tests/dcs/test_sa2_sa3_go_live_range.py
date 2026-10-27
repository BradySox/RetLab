"""SA-2 and SA-3 radars wait until a target is well inside the envelope.

Test 65: MANDRILL fired all 18 SA-2s at flights skirting its ring and was empty
and dark when the DEAD package arrived. The IADS reads the group's first unit,
which is the Flat Face on some layouts and the tracking radar on others.
"""

from __future__ import annotations

import pytest
from dcs.vehicles import AirDefence

from game.dcs.groundunittype import GroundUnitType


@pytest.mark.parametrize(
    "dcs_type",
    [AirDefence.SNR_75V, AirDefence.snr_s_125_tr, AirDefence.p_19_s_125_sr],
)
def test_go_live_at_70_percent(dcs_type: type) -> None:
    for unit_type in GroundUnitType.for_dcs_type(dcs_type):
        assert unit_type.iads_properties.to_dict() == {"go_live_range_in_percent": "70"}
