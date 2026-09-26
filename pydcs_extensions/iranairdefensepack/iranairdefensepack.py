from dcs import unittype

from game.modsupport import vehiclemod

# RetLab Iran Air Defense Pack: 3rd Khordad and Bavar-373. The type ids are the
# contract with the mod's Database lua; ranges are the conservative best
# estimates in docs/dev/design/retlab-iran-air-defense-pack-notes.md.


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
    name = "[IRAD] Bavar-373 TEL (Sayyad-4)"
    detection_range = 0
    threat_range = 150000
    air_weapon_dist = 150000
    eplrs = True


@vehiclemod
class IRAD_Bavar373_LN_4B(unittype.VehicleType):
    id = "IRAD_Bavar373_LN_4B"
    name = "[IRAD] Bavar-373 TEL (Sayyad-4B)"
    detection_range = 0
    threat_range = 200000
    air_weapon_dist = 200000
    eplrs = True


@vehiclemod
class IRAD_Bavar373_TELAR(unittype.VehicleType):
    id = "IRAD_Bavar373_TELAR"
    name = "[IRAD] Bavar-373-II TELAR"
    detection_range = 120000
    threat_range = 200000
    air_weapon_dist = 200000
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
