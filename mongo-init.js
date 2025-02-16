db = db.getSiblingDB("nosql-la-crime");
db.createCollection("crimes");
db.createCollection("victims");
db.createCollection("weapons");
db.createCollection("upvotes");

db.crimes.createIndex({ "DR_NO": 1 }, { unique: true });
db.crimes.createIndex({ "crime_code": 1 });
db.crimes.createIndex({ "date_occurred": -1 });
db.crimes.createIndex({ "location.coordinates": "2dsphere" });

db.victims.createIndex({ "crime_id": 1 });
db.weapons.createIndex({ "crime_id": 1 });
db.upvotes.createIndex({ "crime_id": 1 });
db.upvotes.createIndex({ "officer.email": 1 });
db.upvotes.createIndex({ "officer.badge_number": 1 });

db.upvotes.createIndex({ "upvote_date": 1 }, { expireAfterSeconds: 31536000 }); // Διαγράφει μετά από 1 έτος
