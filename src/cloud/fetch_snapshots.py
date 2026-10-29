"""Freeze the live data the cloud tools use, so evaluation does not depend on live APIs.

  python -m src.cloud.fetch_snapshots places        # geocode the KCC districts -> data/snapshots/places.json (Open-Meteo, no key)
  python -m src.cloud.fetch_snapshots weather       # 7-day forecast per place -> data/snapshots/weather/<Place>_<date>.json
  python -m src.cloud.fetch_snapshots mandi         # Agmarknet prices for UP -> data/snapshots/mandi_<date>.json (needs DATA_GOV_API_KEY)
Snapshots are committed, so rerun only to refresh. Use one date for the whole evaluation.
"""
import json
import os
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

import requests

from src.data.common import read_jsonl

SNAP = Path("data/snapshots")
MANDI_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"  # data.gov.in "Current daily price of commodities (Mandi)"
GEO_FIX = {"Bulandshahar": "Bulandshahr", "Kheri": "Lakhimpur Kheri", "Badaun": "Budaun", "Maharahganj": "Maharajganj",
           "Kushi Nagar": "Kushinagar", "Faizabad": "Ayodhya", "Allahabad": "Prayagraj", "Raebareli": "Rae Bareli",
           "Amethi ( Shahu Ji Maharaj)": "Amethi", "Kanpur Dehat": "Kanpur"}
# Approximate district-HQ coordinates for names the geocoder cannot find (good enough for a district forecast).
COORDS = {"Gonda": (27.13, 81.96), "Barabanki": (26.93, 81.19), "Ambedkar Nagar": (26.43, 82.54), "Sambal (Bhim Nagar)": (28.58, 78.57),
          "Kanpur City": (26.45, 80.35), "Sonbhadra": (24.69, 83.07), "Shamli (Prabudh Nager)": (29.45, 77.31),
          "Jyotiba Phule Nagar": (28.90, 78.47), "Kanshiram Nagar": (27.81, 78.65), "Siddharth Nagar": (27.28, 83.11),
          "Shivasti": (27.68, 81.93), "Gautam Buddha Nagar": (28.54, 77.39), "Hapur (Panchsheel Nagar)": (28.73, 77.78),
          "Kaushambi": (25.53, 81.38), "Sant Kabir Nagar": (26.77, 83.07), "Sant Ravidas Nagar Bhadohi": (25.40, 82.57)}


def places():
    names = [d for d, _ in Counter(q["district"] for q in read_jsonl("data/processed/questions.jsonl") if q["district"]).most_common()]
    out, failed = {}, []
    for n in names:
        r = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": GEO_FIX.get(n, n), "country_code": "IN", "count": 5}, timeout=20).json()
        hit = next((x for x in r.get("results", []) if x.get("admin1") == "Uttar Pradesh"), None)
        if n in COORDS:
            out[n] = {"lat": COORDS[n][0], "lon": COORDS[n][1]}
        elif hit:
            out[n] = {"lat": hit["latitude"], "lon": hit["longitude"]}
        else:
            failed.append(n)
        time.sleep(0.15)
    SNAP.mkdir(parents=True, exist_ok=True)
    (SNAP / "places.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out)} places saved; NOT FOUND (add by hand): {failed}")


def weather():
    today, ps = date.today().isoformat(), json.loads((SNAP / "places.json").read_text(encoding="utf-8"))
    (SNAP / "weather").mkdir(parents=True, exist_ok=True)
    for n, p in ps.items():
        r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=30, params={
            "latitude": p["lat"], "longitude": p["lon"], "timezone": "Asia/Kolkata", "forecast_days": 7,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max"})
        r.raise_for_status()
        (SNAP / "weather" / f"{n.replace(' ', '_')}_{today}.json").write_text(json.dumps(r.json()), encoding="utf-8")
        time.sleep(0.2)
    print(f"{len(ps)} weather snapshots for {today}")


def mandi():
    key = os.environ.get("DATA_GOV_API_KEY")
    if not key:
        sys.exit("Set DATA_GOV_API_KEY in .env (free key from data.gov.in > My Account). MANUAL step, see docs/cloud/MANUAL_TODO.md")
    rows = []
    for commodity in ("Wheat", "Paddy(Dhan)", "Mustard", "Sugarcane"):
        r = requests.get(f"https://api.data.gov.in/resource/{MANDI_RESOURCE}", timeout=60, params={
            "api-key": key, "format": "json", "limit": 1000, "filters[state]": "Uttar Pradesh", "filters[commodity]": commodity}).json()
        for x in r.get("records", []):
            rows.append({"state": x["state"], "district": x["district"], "market": x["market"], "commodity": x["commodity"],
                         "arrival_date": x["arrival_date"], "min_price": x["min_price"], "max_price": x["max_price"], "modal_price": x["modal_price"]})
    (SNAP / f"mandi_{date.today().isoformat()}.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    print(f"{len(rows)} mandi rows saved")


if __name__ == "__main__":
    from src.eval.judge import load_env
    load_env()
    {"places": places, "weather": weather, "mandi": mandi}[sys.argv[1]]()
