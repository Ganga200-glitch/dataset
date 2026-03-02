#!/usr/bin/env python3

import os
import time
import json
import threading
import requests
from datetime import datetime, timezone
from flask import Flask
import firebase_admin
from firebase_admin import credentials, db

# ------------------------------
# FLASK APP (REQUIRED FOR RENDER)
# ------------------------------

app = Flask(__name__)

@app.route("/")
def home():
    return "Traffic Collector Running ✅"

# ------------------------------
# CONFIG
# ------------------------------

BASE_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

LOCATIONS = {
    "Central Junction": (10.064118, 76.629489),
    "MC Road Segment": (10.063980, 76.633200),
    "Market Area": (10.060950, 76.626500),
}

# ------------------------------
# INITIALIZE FIREBASE
# ------------------------------

def initialize_firebase():
    firebase_key_json = os.getenv("FIREBASE_KEY")
    firebase_key_dict = json.loads(firebase_key_json)

    cred = credentials.Certificate(firebase_key_dict)

    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://kothamangalam-traffic-default-rtdb.firebaseio.com/'
    })

# ------------------------------
# TRAFFIC COLLECTOR LOOP
# ------------------------------

def traffic_collector():
    api_key = os.getenv("TOMTOM_API_KEY")
    ref = db.reference("traffic_data")

    print("Traffic collector started...")

    while True:
        for name, (lat, lon) in LOCATIONS.items():
            try:
                timestamp = datetime.now(timezone.utc).isoformat()

                params = {
                    "point": f"{lat},{lon}",
                    "key": api_key
                }

                response = requests.get(BASE_URL, params=params)
                data = response.json()
                flow = data.get("flowSegmentData", {})

                current_speed = float(flow.get("currentSpeed", 0))
                free_flow_speed = float(flow.get("freeFlowSpeed", 0))
                confidence = flow.get("confidence", 0)

                congestion_index = 0.0
                if free_flow_speed > 0:
                    congestion_index = (free_flow_speed - current_speed) / free_flow_speed

                upload_data = {
                    "timestamp": timestamp,
                    "location": name,
                    "current_speed": current_speed,
                    "free_flow_speed": free_flow_speed,
                    "congestion_index": congestion_index,
                    "confidence": confidence
                }

                ref.push(upload_data)

                print(f"Uploaded data for {name}")

            except Exception as e:
                print(f"Error: {e}")

        print("Sleeping 15 minutes...")
        time.sleep(900)


# ------------------------------
# START EVERYTHING
# ------------------------------

if __name__ == "__main__":

    initialize_firebase()

    # Start background thread
    thread = threading.Thread(target=traffic_collector)
    thread.daemon = True
    thread.start()

    # Run Flask app (Render needs this)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)