from dcs import unittype

from game.modsupport import vehiclemod

# RetLab Iran Air Defense Pack: 3rd Khordad, Bavar-373 and five surface-to-surface
# launchers. The type ids are the contract with the mod's Database lua; ranges are
# the best estimates in docs/dev/design/retlab-iran-air-defense-pack-notes.md.


@vehiclemod
class IRAD_Bashir_SR(unittype.VehicleType):
    id = "IRAD_Bashir_SR"
    name = "[IRAD] 3rd Khordad Bashir SR"
    detection_range = 200000
    threat_range = 0
    air_weapon_dist = 0
    eplrs = True


@vehiclemod
class IRAD_3Khordad_TELAR(unittype.VehicleType):
    id = "IRAD_3Khordad_TELAR"
    name = "[IRAD] 3rd Khordad TELAR"
    detection_range = 90000
    threat_range = 50000
    air_weapon_dist = 50000
    eplrs = True


@vehiclemod
class IRAD_AlamAlHoda_TEL(unittype.VehicleType):
    id = "IRAD_AlamAlHoda_TEL"
    name = "[IRAD] 3rd Khordad Alam al-Hoda TEL"
    detection_range = 0
    threat_range = 50000
    air_weapon_dist = 50000
    eplrs = True


@vehiclemod
class IRAD_Meraj4_SR(unittype.VehicleType):
    id = "IRAD_Meraj4_SR"
    name = "[IRAD] Bavar-373 Meraj-4 SR"
    detection_range = 250000
    threat_range = 0
    air_weapon_dist = 0
    eplrs = True


@vehiclemod
class IRAD_Hafez_SR(unittype.VehicleType):
    id = "IRAD_Hafez_SR"
    name = "[IRAD] Bavar-373 Hafez AR"
    detection_range = 200000
    threat_range = 0
    air_weapon_dist = 0
    eplrs = True


@vehiclemod
class IRAD_Bavar373_STR(unittype.VehicleType):
    id = "IRAD_Bavar373_STR"
    name = "[IRAD] Bavar-373 STR"
    detection_range = 200000
    threat_range = 0
    air_weapon_dist = 0
    eplrs = True


@vehiclemod
class IRAD_Bavar373_CP(unittype.VehicleType):
    id = "IRAD_Bavar373_CP"
    name = "[IRAD] Bavar-373 CP"
    detection_range = 0
    threat_range = 0
    air_weapon_dist = 0
    eplrs = True


@vehiclemod
class IRAD_Bavar373_LN(unittype.VehicleType):
    id = "IRAD_Bavar373_LN"
    name = "[IRAD] Bavar-373 TEL"
    detection_range = 0
    threat_range = 160000
    air_weapon_dist = 160000
    eplrs = True


@vehiclemod
class IRAD_MatlaUlFajr_EWR(unittype.VehicleType):
    id = "IRAD_MatlaUlFajr_EWR"
    name = "[IRAD] Matla ul-Fajr EWR"
    detection_range = 250000
    threat_range = 0
    air_weapon_dist = 0
    eplrs = True


@vehiclemod
class IRAD_Rasool_Comms(unittype.VehicleType):
    id = "IRAD_Rasool_Comms"
    name = "[IRAD] Rasool Comms Shelter"
    detection_range = 0
    threat_range = 0
    air_weapon_dist = 0
    eplrs = True


# Surface-to-surface launchers: missile sites pick a target inside threat_range,
# the mod's own GT.ThreatRange. The four ballistic missiles fly ED's ballistic model with
# motors sized for 150-900 km (DM call 2026-09-30), not their published ranges.
BALLISTIC_MIN_RANGE_M = 150000
BALLISTIC_MAX_RANGE_M = 900000


@vehiclemod
class IRAD_Sejjil_TEL(unittype.VehicleType):
    id = "IRAD_Sejjil_TEL"
    name = "[IRAD] Sejjil-2 TEL"
    detection_range = 0
    threat_range = BALLISTIC_MAX_RANGE_M
    air_weapon_dist = 0


@vehiclemod
class IRAD_Emad_TEL(unittype.VehicleType):
    id = "IRAD_Emad_TEL"
    name = "[IRAD] Emad TEL"
    detection_range = 0
    threat_range = BALLISTIC_MAX_RANGE_M
    air_weapon_dist = 0


@vehiclemod
class IRAD_Kheibar_TEL(unittype.VehicleType):
    id = "IRAD_Kheibar_TEL"
    name = "[IRAD] Kheibar (Khorramshahr-4) TEL"
    detection_range = 0
    threat_range = BALLISTIC_MAX_RANGE_M
    air_weapon_dist = 0


@vehiclemod
class IRAD_Fattah2_TEL(unittype.VehicleType):
    id = "IRAD_Fattah2_TEL"
    name = "[IRAD] Fattah-2 TEL"
    detection_range = 0
    threat_range = BALLISTIC_MAX_RANGE_M
    air_weapon_dist = 0


@vehiclemod
class IRAD_Shahed238_TEL(unittype.VehicleType):
    id = "IRAD_Shahed238_TEL"
    name = "[IRAD] Shahed 238 launcher"
    detection_range = 0
    threat_range = 1000000
    air_weapon_dist = 0


#: The closest a missile site of these types may fire; the mod's launchers refuse nearer.
MISSILE_MIN_RANGE_M: dict[str, int] = {
    IRAD_Sejjil_TEL.id: BALLISTIC_MIN_RANGE_M,
    IRAD_Emad_TEL.id: BALLISTIC_MIN_RANGE_M,
    IRAD_Kheibar_TEL.id: BALLISTIC_MIN_RANGE_M,
    IRAD_Fattah2_TEL.id: BALLISTIC_MIN_RANGE_M,
}


#: Launchers a site spawns with on red alert. Under Skynet on AUTO the Bavar-373 TELs never
#: raised (tests 48-49); set red in the Mission Editor they did.
ALARM_RED_AT_SPAWN: set[str] = {IRAD_Bavar373_LN.id}
