import pandas as pd
from pymongo import MongoClient
import os

# Σύνδεση με MongoDB
MONGO_URI = os.getenv("DATABASE_URL", "mongodb://admin:secret@localhost:27017/nosql-la-crime?authSource=admin")
client = MongoClient(MONGO_URI)
db = client["nosql-la-crime"]

# Φόρτωση των δεδομένων
print("📂 Φόρτωση δεδομένων...")
df = pd.read_csv("crime_data.csv")

# Καθαρισμός παλαιών δεδομένων
db.crimes.delete_many({})
db.victims.delete_many({})
db.weapons.delete_many({})
db.upvotes.delete_many({})

crimes = []
victims = []
weapons = []
print("📝 Εισαγωγή δεδομένων στη βάση...")
for _, row in df.iterrows():
    crime_doc = {
        "DR_NO": row["DR_NO"],
        "date_reported": row["Date Rptd"],
        "date_occurred": row["DATE OCC"],
        "time_occurred": row["TIME OCC"],
        "area": { "id": row["AREA"], "name": row["AREA NAME"], "reporting_district": row["Rpt Dist No"] },
        "crime_code": row["Crm Cd"],
        "crime_description": row["Crm Cd Desc"],
        "status": { "code": row["Status"], "description": row["Status Desc"] },
        "location": {
            "address": row["LOCATION"],
            "coordinates": [row["LON"], row["LAT"]] if pd.notna(row["LON"]) and pd.notna(row["LAT"]) else None
        }
    }
    
    crime_id = db.crimes.insert_one(crime_doc).inserted_id

    if not pd.isna(row["Vict Age"]) or not pd.isna(row["Vict Sex"]) or not pd.isna(row["Vict Descent"]):
        victim_doc = {
            "crime_id": crime_id,
            "age": row["Vict Age"] if pd.notna(row["Vict Age"]) else None,
            "sex": row["Vict Sex"] if pd.notna(row["Vict Sex"]) else None,
            "descent": row["Vict Descent"] if pd.notna(row["Vict Descent"]) else None
        }
        victims.append(victim_doc)
    
    if not pd.isna(row["Weapon Used Cd"]):
        weapon_doc = {
            "crime_id": crime_id,
            "weapon_code": row["Weapon Used Cd"],
            "weapon_description": row["Weapon Desc"]
        }
        weapons.append(weapon_doc)

# Μαζική εισαγωγή στα collections
if victims:
    db.victims.insert_many(victims)

if weapons:
    db.weapons.insert_many(weapons)

print(f"✅ Εισήχθησαν {len(df)} εγκλήματα στη MongoDB!")
