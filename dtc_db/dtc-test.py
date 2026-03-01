from python.dtc_database import DTCDatabase

db = DTCDatabase()

dtc = db.get_dtc("P0420")
print(dtc.code, dtc.type_name, dtc.description)

ford_specific = db.get_dtc("P1690", "FORD")
print(ford_specific)