#!/usr/bin/env python3

import os
import time
import requests
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db

# ------------------------------
# CONFIGURATION
# ------------------------------

BASE_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

LOCATIONS = {
    "Central Junction": (10.064118, 76.629489),
    "MC Road Segment": (10.063980, 76.633200),
    "Market Area": (10.060950, 76.626500),
}

# ------------------------------
# GET API KEY
# ------------------------------

def get_api_key():
    key = os.getenv("TOMTOM_API_KEY")
    if key:
        return key
    return input("Enter your TomTom API key: ").strip()

# ------------------------------
# FETCH TRAFFIC DATA
# ------------------------------

def fetch_flow(lat, lon, api_key):
    params = {
        "point": f"{lat},{lon}",
        "key": api_key
    }
    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

# ------------------------------
# CALCULATE CONGESTION
# ------------------------------

def compute_congestion_index(free_flow_speed, current_speed):
    if free_flow_speed and free_flow_speed > 0:
        return (free_flow_speed - current_speed) / free_flow_speed
    return 0.0

# ------------------------------
# MAIN PROGRAM
# ------------------------------

def main():

    # 🔐 Initialize Firebase
    import json

    firebase_key_json = os.getenv("FIREBASE_KEY")
    firebase_key_dict = json.loads(firebase_key_json)

    cred = credentials.Certificate(firebase_key_dict)

    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://kothamangalam-traffic.firebaseio.com/'
    })

    ref = db.reference("traffic_data")

    api_key = get_api_key()
    if not api_key:
        print("No API key provided.")
        return

    print("Traffic collector started...")

    while True:
        for name, (lat, lon) in LOCATIONS.items():
            try:
                timestamp = datetime.utcnow().isoformat()

                data = fetch_flow(lat, lon, api_key)
                flow = data.get("flowSegmentData", {})

                current_speed = float(flow.get("currentSpeed", 0))
                free_flow_speed = float(flow.get("freeFlowSpeed", 0))
                confidence = flow.get("confidence", 0)

                congestion_index = compute_congestion_index(
                    free_flow_speed,
                    current_speed
                )

                upload_data = {
                    "timestamp": timestamp,
                    "location": name,
                    "current_speed": current_speed,
                    "free_flow_speed": free_flow_speed,
                    "congestion_index": congestion_index,
                    "confidence": confidence
                }

                ref.push(upload_data)

                print(f"Uploaded data for {name} at {timestamp}")

            except Exception as e:
                print(f"Error for {name}: {e}")

        print("Sleeping 15 minutes...\n")
        time.sleep(900)  # 15 minutes


if __name__ == "__main__":
    main()