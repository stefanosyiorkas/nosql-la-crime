from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
import os
import random
import math
from pydantic import BaseModel, EmailStr
from bson import ObjectId
from datetime import datetime, timedelta

MONGO_URI = os.getenv("DATABASE_URL")
app = FastAPI()
client = AsyncIOMotorClient(MONGO_URI)
db = client["nosql-la-crime"]

def clean_data(doc):
    """Καθαρίζει το έγγραφο ώστε να είναι συμβατό με JSON"""
    if doc is None:
        return None
    for key, value in doc.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            doc[key] = None  # Αντικατάσταση NaN / Infinity με None
        elif isinstance(value, dict):
            doc[key] = clean_data(value)  # Αναδρομικός έλεγχος
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])  # Μετατροπή του ObjectId σε str
    return doc

@app.get("/api/random_crime")
async def get_random_crime():
    """ Επιστροφή ενός τυχαίου εγκλήματος """
    crimes = await db.crimes.find().to_list(1000)
    if not crimes:
        raise HTTPException(status_code=404, detail="No crimes found")

    crime = random.choice(crimes)
    return clean_data(crime)

from datetime import datetime

@app.get("/api/crimes/count-by-code")
async def count_by_crime_code(start_date: str, end_date: str):
    """ Επιστροφή του αριθμού αναφορών ανά `Crm Cd` σε συγκεκριμένο χρονικό διάστημα (φθίνουσα σειρά) """
    try:
        start_date = datetime.strptime(start_date, "%m/%d/%Y")
        end_date = datetime.strptime(end_date, "%m/%d/%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use MM/DD/YYYY")

    pipeline = [
        {"$match": {
            "date_occurred": {"$gte": start_date.strftime("%m/%d/%Y"), "$lte": end_date.strftime("%m/%d/%Y")}
        }},
        {"$group": {"_id": "$crime_code", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    results = await db.crimes.aggregate(pipeline).to_list(None)
    return [{"crime_code": r["_id"], "count": r["count"]} for r in results]

@app.get("/api/crimes/daily-count")
async def daily_count_by_crime_code(crime_code: int, start_date: str, end_date: str):
    """ Επιστροφή του συνολικού αριθμού αναφορών ανά ημέρα για συγκεκριμένο `Crm Cd` και χρονικό διάστημα """
    try:
        start_date_dt = datetime.strptime(start_date, "%m/%d/%Y")
        end_date_dt = datetime.strptime(end_date, "%m/%d/%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use MM/DD/YYYY")

    # Δημιουργούμε όλες τις ημερομηνίες στο χρονικό διάστημα
    current_date = start_date_dt
    all_dates = []
    while current_date <= end_date_dt:
        date_str = current_date.strftime("%m/%d/%Y")  # Αφαιρούμε την ώρα
        all_dates.append(date_str)
        current_date += timedelta(days=1)

    # Query για να φέρει όλες τις ημερομηνίες που υπάρχουν στη βάση
    pipeline = [
        {"$match": {
            "crime_code": crime_code,
            "date_occurred": {"$regex": "|".join([f"^{d}" for d in all_dates])}  # Regex για εύκολη αναζήτηση ημερομηνίας
        }},
        {"$group": {"_id": "$date_occurred", "report_count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]

    results = await db.crimes.aggregate(pipeline).to_list(None)

    # Δημιουργούμε dictionary με τα αποτελέσματα από τη βάση
    result_dict = {r["_id"].split(" ")[0]: r["report_count"] for r in results}

    # Επιστρέφουμε όλες τις ημερομηνίες, ακόμα και αν δεν υπάρχουν αναφορές (βάζουμε 0)
    full_results = [{"date": date, "report_count": result_dict.get(date, 0)} for date in all_dates]

    return full_results

@app.get("/api/crimes/most-common")
async def most_common_crimes_per_area(date: str):
    """ Βρίσκει τα τρία πιο κοινά εγκλήματα ανά περιοχή για μια συγκεκριμένη ημέρα """
    try:
        date_dt = datetime.strptime(date, "%m/%d/%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use MM/DD/YYYY")

    formatted_date = date_dt.strftime("%m/%d/%Y")  # Αφαιρούμε την ώρα από το query

    pipeline = [
        {"$match": {"date_occurred": {"$regex": f"^{formatted_date}"}}},  # Regex για ημερομηνία χωρίς ώρα
        {"$group": {"_id": {"area": "$area.name", "crime": "$crime_description"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$group": {"_id": "$_id.area", "crimes": {"$push": {"crime": "$_id.crime", "count": "$count"}}}},
        {"$project": {"area": "$_id", "crimes": {"$slice": ["$crimes", 3]}}},
        {"$sort": {"area": 1}}
    ]
    
    results = await db.crimes.aggregate(pipeline).to_list(None)
    return results

@app.get("/api/crimes/least-common")
async def least_common_crimes(start_date: str, end_date: str):
    """ Βρίσκει τα δύο λιγότερο κοινά εγκλήματα για συγκεκριμένο χρονικό διάστημα """
    try:
        start_date_dt = datetime.strptime(start_date, "%m/%d/%Y")
        end_date_dt = datetime.strptime(end_date, "%m/%d/%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use MM/DD/YYYY")

    formatted_start_date = start_date_dt.strftime("%m/%d/%Y")
    formatted_end_date = end_date_dt.strftime("%m/%d/%Y")

    pipeline = [
        {"$match": {"date_occurred": {"$regex": f"^({formatted_start_date}|{formatted_end_date})"}}},
        {"$group": {"_id": "$crime_description", "count": {"$sum": 1}}},
        {"$sort": {"count": 1}},
        {"$limit": 2}
    ]
    
    results = await db.crimes.aggregate(pipeline).to_list(None)
    return [{"crime": r["_id"], "count": r["count"]} for r in results]

@app.get("/api/crimes/weapons-used")
async def weapons_used_per_crime(crime_code: int):
    """ Βρίσκει όλους τους τύπους όπλων που χρησιμοποιήθηκαν για το ίδιο `Crm Cd` σε διαφορετικές περιοχές """
    pipeline = [
        {"$match": {"crime_code": crime_code}},  # Βρίσκουμε τα εγκλήματα με τον συγκεκριμένο Crime Code
        {"$lookup": {
            "from": "weapons",  # Σύνδεση με το collection weapons
            "localField": "_id",
            "foreignField": "crime_id",
            "as": "weapon_data"
        }},
        {"$unwind": "$weapon_data"},  # Ξεδιπλώνουμε τα στοιχεία των όπλων
        {"$group": {
            "_id": {"area": "$area.name", "weapon": "$weapon_data.weapon_description"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.area": 1, "count": -1}},  # Ταξινόμηση ανά περιοχή και αριθμό χρήσεων
        {"$group": {
            "_id": "$_id.area",
            "weapons": {"$push": {"weapon": "$_id.weapon", "count": "$count"}}
        }},
        {"$project": {"area": "$_id", "weapons": 1}}
    ]
    
    results = await db.crimes.aggregate(pipeline).to_list(None)
    
    if not results:
        return {"message": "No weapon data found for the given crime code"}
    
    return results



class UpvoteRequest(BaseModel):
    crime_id: str
    officer_name: str
    officer_badge: str
    officer_email: EmailStr

@app.post("/api/crimes/upvote")
async def upvote_crime(upvote_data: UpvoteRequest):
    """ Επιτρέπει σε έναν αστυνομικό να δώσει upvote σε μια αναφορά εγκλήματος """
    
    # Μετατροπή του crime_id σε ObjectId για τη MongoDB
    try:
        crime_object_id = ObjectId(upvote_data.crime_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid crime_id format")

    # Έλεγχος αν υπάρχει το έγκλημα στη βάση
    crime = await db.crimes.find_one({"_id": crime_object_id})
    if not crime:
        raise HTTPException(status_code=404, detail="Crime record not found")

    # Έλεγχος αν ο αστυνομικός έχει ήδη ψηφίσει για το συγκεκριμένο crime_id
    existing_upvote = await db.upvotes.find_one({
        "crime_id": crime_object_id,
        "officer.badge_number": upvote_data.officer_badge
    })
    if existing_upvote:
        raise HTTPException(status_code=400, detail="Officer has already upvoted this crime record")

    # Δημιουργία του upvote record
    upvote_record = {
        "crime_id": crime_object_id,
        "officer": {
            "badge_number": upvote_data.officer_badge,
            "name": upvote_data.officer_name,
            "email": upvote_data.officer_email
        },
        "upvote_date": datetime.utcnow().strftime("%Y-%m-%d")
    }

    # Εισαγωγή του upvote στη βάση
    await db.upvotes.insert_one(upvote_record)
    return {"message": "Upvote registered successfully"}

@app.get("/api/crimes/top-upvoted")
async def top_upvoted_reports(date: str):
    """ Βρίσκει τις 50 πιο upvoted αναφορές για μια συγκεκριμένη ημέρα """
    try:
        date_dt = datetime.strptime(date, "%m/%d/%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use MM/DD/YYYY")

    formatted_date = date_dt.strftime("%m/%d/%Y")  # Μορφή που ταιριάζει με τη βάση

    pipeline = [
        {"$match": {"date_occurred": {"$regex": f"^{formatted_date}"}}},  # Φιλτράρουμε για τη συγκεκριμένη ημερομηνία
        {"$lookup": {
            "from": "upvotes",  
            "localField": "_id",  
            "foreignField": "crime_id",  
            "as": "upvote_data"
        }},
        {"$addFields": {"upvote_count": {"$size": "$upvote_data"}}},  # Μετράμε τα upvotes
        {"$sort": {"upvote_count": -1}},  # Ταξινομούμε φθίνουσα βάση των upvotes
        {"$limit": 50},  # Επιστρέφουμε τις 50 πιο upvoted αναφορές
        {"$project": {
            "_id": 0,
            "DR_NO": 1,
            "crime_description": 1,
            "area.name": 1,
            "date_occurred": 1,
            "upvote_count": 1
        }}
    ]
    
    results = await db.crimes.aggregate(pipeline).to_list(None)
    
    if not results:
        return {"message": "No upvoted reports found for the given date"}
    
    return results

@app.get("/api/officers/top-active")
async def top_active_officers():
    """ Βρίσκει τους 50 πιο ενεργούς αστυνομικούς με βάση τον αριθμό των upvotes που έχουν δώσει """
    
    pipeline = [
        {"$group": {"_id": "$officer.badge_number", "name": {"$first": "$officer.name"}, "email": {"$first": "$officer.email"}, "upvote_count": {"$sum": 1}}},
        {"$sort": {"upvote_count": -1}},  # Ταξινόμηση φθίνουσα βάση των upvotes
        {"$limit": 50},  # Περιορίζουμε στα 50 κορυφαία αποτελέσματα
        {"$project": {"_id": 0, "badge_number": "$_id", "name": 1, "email": 1, "upvote_count": 1}}
    ]
    
    results = await db.upvotes.aggregate(pipeline).to_list(None)
    
    if not results:
        return {"message": "No officer upvote data found"}
    
    return results

@app.get("/api/officers/top-by-area")
async def top_officers_by_area():
    """ Βρίσκει τους 50 αστυνομικούς που έχουν κάνει upvotes σε εγκλήματα σε διαφορετικές περιοχές """
    
    pipeline = [
        {"$lookup": {
            "from": "crimes",
            "localField": "crime_id",
            "foreignField": "_id",
            "as": "crime_data"
        }},
        {"$unwind": "$crime_data"},  # Ξεδιπλώνουμε τα δεδομένα των εγκλημάτων
        {"$group": {
            "_id": {"badge_number": "$officer.badge_number", "name": "$officer.name", "email": "$officer.email"},
            "unique_areas": {"$addToSet": "$crime_data.area.name"}  # Μετράμε τις μοναδικές περιοχές
        }},
        {"$project": {
            "badge_number": "$_id.badge_number",
            "name": "$_id.name",
            "email": "$_id.email",
            "unique_area_count": {"$size": "$unique_areas"}
        }},
        {"$sort": {"unique_area_count": -1}},  # Ταξινόμηση φθίνουσα βάση των μοναδικών περιοχών
        {"$limit": 50}  # Περιορίζουμε στα 50 κορυφαία αποτελέσματα
    ]
    
    results = await db.upvotes.aggregate(pipeline).to_list(None)
    
    if not results:
        return {"message": "No officer area data found"}
    
    return results

@app.get("/api/upvotes/multiple-badge")
async def upvotes_with_multiple_badges():
    """ Βρίσκει αναφορές που έχουν λάβει upvotes από το ίδιο email αλλά με διαφορετικά badge numbers """
    
    pipeline = [
        {"$group": {
            "_id": {"crime_id": "$crime_id", "email": "$officer.email"},
            "unique_badges": {"$addToSet": "$officer.badge_number"}  # Διατηρούμε μοναδικά badge numbers
        }},
        {"$match": {"unique_badges.1": {"$exists": True}}},  # Κρατάμε μόνο όσους έχουν πάνω από 1 μοναδικό badge
        {"$lookup": {
            "from": "crimes",
            "localField": "_id.crime_id",
            "foreignField": "_id",
            "as": "crime_data"
        }},
        {"$unwind": "$crime_data"},
        {"$project": {
            "_id": 0,
            "crime_id": "$_id.crime_id",
            "email": "$_id.email",
            "badge_numbers": "$unique_badges",
            "crime_description": "$crime_data.crime_description",
            "date_occurred": "$crime_data.date_occurred",
            "area": "$crime_data.area.name"
        }},
        {"$sort": {"date_occurred": 1}}  # Ταξινόμηση βάσει ημερομηνίας
    ]
    
    results = await db.upvotes.aggregate(pipeline).to_list(None)
    
    if not results:
        return {"message": "No duplicate badge upvotes found"}
    
    return results

@app.get("/api/officers/upvoted-areas")
async def upvoted_areas_by_officer(officer_name: str):
    """ Βρίσκει όλες τις περιοχές όπου ένας συγκεκριμένος αστυνομικός έχει δώσει upvote σε reports που αφορούν την περιοχή """
    
    pipeline = [
        {"$match": {"officer.name": officer_name}},  # Φιλτράρουμε τα upvotes του συγκεκριμένου αστυνομικού
        {"$lookup": {
            "from": "crimes",
            "localField": "crime_id",
            "foreignField": "_id",
            "as": "crime_data"
        }},
        {"$unwind": "$crime_data"},  # Ξεδιπλώνουμε τα δεδομένα των εγκλημάτων
        {"$group": {"_id": "$crime_data.area.name"}},  # Ομαδοποιούμε ανά περιοχή
        {"$project": {"_id": 0, "area": "$_id"}},  # Μόνο η περιοχή στα αποτελέσματα
        {"$sort": {"area": 1}}  # Ταξινόμηση αλφαβητικά
    ]
    
    results = await db.upvotes.aggregate(pipeline).to_list(None)
    
    if not results:
        return {"message": "No upvoted areas found for the given officer name"}
    
    return results

from pydantic import BaseModel
from typing import Optional

class CrimeReport(BaseModel):
    DR_NO: int
    date_reported: str
    date_occurred: str
    time_occurred: int
    area: dict
    crime_code: int
    crime_description: str
    status: dict
    location: dict

@app.post("/api/crimes/insert")
async def insert_crime_report(report: CrimeReport):
    """ Προσθήκη νέας αναφοράς εγκλήματος """
    
    # Έλεγχος αν υπάρχει ήδη το DR_NO
    existing_crime = await db.crimes.find_one({"DR_NO": report.DR_NO})
    if existing_crime:
        raise HTTPException(status_code=400, detail="Crime report already exists")
    
    # Εισαγωγή στη βάση
    crime_doc = report.dict()
    inserted_crime = await db.crimes.insert_one(crime_doc)

    return {"message": "Crime report inserted successfully", "crime_id": str(inserted_crime.inserted_id)}
