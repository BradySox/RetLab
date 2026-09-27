# Iranian ballistic-missile launchers from three third-party mods, supported until the
# RetLab Iran Air Defense Pack carries its own (DM call 2026-09-27; see
# docs/dev/design/retlab-iran-iads-deployment-notes.md). Requires all three:
#   PG Iran IRBM Pack (Sejjil-2, Emad, Fattah-2), PG Iran Air Defense Pack (Shahed-238),
#   Kheibar (Khorramshahr-4) TEL.
# Ranges are each mod's own GT.ThreatRange; missile sites pick targets inside it.

from dcs import unittype

from game.modsupport import vehiclemod


@vehiclemod
class PGIR_Sejjil_Launcher(unittype.VehicleType):
    id = "PGIR_Sejjil_Launcher"
    name = "Sejjil-2 MRBM TEL [PG IR]"
    detection_range = 0
    threat_range = 2000000
    air_weapon_dist = 0


@vehiclemod
class PGIR_Emad_Launcher(unittype.VehicleType):
    id = "PGIR_Emad_Launcher"
    name = "Emad MRBM TEL [PG IR]"
    detection_range = 0
    threat_range = 1700000
    air_weapon_dist = 0


@vehiclemod
class PGIR_Fattah2_Launcher(unittype.VehicleType):
    id = "PGIR_Fattah2_Launcher"
    name = "Fattah-2 HGV TEL [PG IR]"
    detection_range = 0
    threat_range = 1400000
    air_weapon_dist = 0


@vehiclemod
class PGAD_Shahed238_TEL(unittype.VehicleType):
    id = "PGAD_Shahed238_TEL"
    name = "Shahed 238 LM [PG AD]"
    detection_range = 0
    threat_range = 1000000
    air_weapon_dist = 0


@vehiclemod
class KHEIBAR_TEL_Launcher(unittype.VehicleType):
    id = "KHEIBAR_TEL_Launcher"
    name = "Kheibar (Khorramshahr-4) TEL"
    detection_range = 0
    threat_range = 2000000
    air_weapon_dist = 0
