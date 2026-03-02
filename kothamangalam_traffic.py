#!/usr/bin/env python3
"""
Collects real-time traffic flow data from TomTom for three Kothamangalam locations
and appends rows to kothamangalam_traffic_dataset.csv.

Usage:
 - Set environment variable TOMTOM_API_KEY or the script will prompt for it.
 - Run: python kothamangalam_traffic.py
"""
import os
import csv
import requests
from datetime import datetime

CSV_FILE = "kothamangalam_traffic_dataset.csv"
BASE_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

LOCATIONS = {
    "Central Junction": (10.064118, 76.629489),
    "MC Road Segment": (10.063980, 76.633200),
    "Market Area": (10.060950, 76.626500),
}


def get_api_key():
    key = os.getenv("TOMTOM_API_KEY")
    if key:
        return key
    try:
        # fallback: prompt the user
        return input("Enter your TomTom API key: ").strip()
    except Exception:
        return None


def fetch_flow(lat, lon, api_key):
    params = {"point": f"{lat},{lon}", "key": api_key}
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def parse_flow(json_data):
    flow = json_data.get("flowSegmentData", {})
    current_speed = flow.get("currentSpeed")
    free_flow_speed = flow.get("freeFlowSpeed")
    current_travel_time = flow.get("currentTravelTime")
    confidence = flow.get("confidence")
    return current_speed, free_flow_speed, current_travel_time, confidence


def compute_congestion_index(free_flow_speed, current_speed):
    try:
        if free_flow_speed and free_flow_speed > 0:
            return (free_flow_speed - current_speed) / free_flow_speed
    except Exception:
        pass
    return 0.0


def ensure_csv_header(path):
    if not os.path.exists(path):
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "location", "current_speed", "free_flow_speed", "congestion_index", "confidence"])


def append_row(path, row):
    with open(path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def main():
    api_key = get_api_key()
    if not api_key:
        print("No TomTom API key provided. Set TOMTOM_API_KEY or provide one when prompted.")
        return

    ensure_csv_header(CSV_FILE)

    for name, (lat, lon) in LOCATIONS.items():
        timestamp = datetime.utcnow().isoformat()
        try:
            data = fetch_flow(lat, lon, api_key)
            current_speed, free_flow_speed, _, confidence = parse_flow(data)

            # Ensure numeric values
            if current_speed is None:
                current_speed = 0.0
            if free_flow_speed is None:
                free_flow_speed = 0.0
            try:
                current_speed = float(current_speed)
            except Exception:
                current_speed = 0.0
            try:
                free_flow_speed = float(free_flow_speed)
            except Exception:
                free_flow_speed = 0.0

            congestion_index = compute_congestion_index(free_flow_speed, current_speed)

            row = [timestamp, name, current_speed, free_flow_speed, congestion_index, confidence]
            append_row(CSV_FILE, row)
            print(f"Saved row for '{name}' at {timestamp}")
        except requests.HTTPError as e:
            print(f"HTTP error for {name} ({lat},{lon}): {e}")
        except requests.RequestException as e:
            print(f"Request error for {name} ({lat},{lon}): {e}")
        except Exception as e:
            print(f"Unexpected error for {name} ({lat},{lon}): {e}")


if __name__ == "__main__":
    main()
