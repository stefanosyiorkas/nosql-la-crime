# NoSQL LA Crime API - MongoDB & FastAPI

## 📌 Description
This application is built using **FastAPI** and **MongoDB** to manage crime records from the Los Angeles Police Department (LAPD). It supports:
- **Crime record searches** based on various criteria.
- **Adding new crime reports.**
- **Upvote system** for police officers to highlight important reports.

---

## 🛠️ Technologies
- **Python** (FastAPI, Pydantic, Motor)
- **MongoDB** (NoSQL Database)
- **Docker & Docker Compose** (For easy deployment)

---

## 🚀 Running Instructions

### **1️⃣ Prerequisites**
- Installed **Docker** and **Docker Compose**
- **Python 3.10+** (if you want to run the API outside of Docker)

### **2️⃣ Running with Docker**
To start the application, simply execute:
```sh
docker compose up -d --build
```
This will start the following services:
- **MongoDB** (Database)
- **Mongo Express** (Database management at `http://localhost:8081`)
- **FastAPI** (REST API at `http://localhost:8000`)

### **3️⃣ Import Data**
After starting the containers, download the crime data file from

https://data.lacity.org/Public-Safety/Crime-Data-from-2020-to-Present/2nrs-mtv8/about_data 

and place it to the root directory of the project with the name **crime_data.csv**. Then execute the following command to import data:
```sh
python import_crime_data.py
```

### **4️⃣ Test the API**
You can test the API using **Swagger UI**:
- Open `http://localhost:8000/docs`

---

## 📌 Key Endpoints

### 🔹 **1. Retrieve crimes for a specific `crime_code` and time range**
```sh
GET /api/crimes/daily-count?crime_code=510&start_date=01/01/2023&end_date=01/01/2024
```

### 🔹 **2. Insert a new crime report**
```sh
POST /api/crimes/insert
```
**Body:**
```json
{
    "DR_NO": 190326999,
    "date_reported": "02/10/2025 12:00:00 AM",
    "date_occurred": "02/10/2025 12:00:00 AM",
    "time_occurred": 1330,
    "area": {"id": 5, "name": "Central", "reporting_district": 321},
    "crime_code": 626,
    "crime_description": "ROBBERY",
    "status": {"code": "AA", "description": "Adult Arrest"},
    "location": {"address": "500 S Main St", "coordinates": [-118.2500, 34.0500]}
}
```

### 🔹 **3. Register Upvote from a Police Officer**
```sh
POST /api/crimes/upvote
```
**Body:**
```json
{
    "crime_id": "67aa98fc0947c75e60e67ca5",
    "officer_name": "John Doe",
    "officer_badge": "123456",
    "officer_email": "jdoe@lapd.gov"
}
```

### 🔹 **4. Retrieve the 50 most upvoted crime reports for a specific day**
```sh
GET /api/crimes/top-upvoted?date=01/01/2023
```

### 🔹 **5. Retrieve the 50 most active police officers (based on upvotes given)**
```sh
GET /api/officers/top-active
```

---

## 🛠️ Managing the Database via Mongo Express
You can view the database data through **Mongo Express**:
- Open `http://localhost:8081`
- Username: `admin`, Password: `secret`

---

## ⚡ Useful MongoDB Commands
To check how many crime records exist:
```sh
docker exec -it nosql-la-crime-mongo mongosh -u admin -p secret --authenticationDatabase admin
```
Inside the MongoDB shell:
```js
use nosql-la-crime;
db.crimes.countDocuments();
db.crimes.findOne();
```

---

## ✅ Final Notes
This application is **optimized for efficiency**, with **proper use of indexes**, ensuring it can handle **large volumes of data** effectively.