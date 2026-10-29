"""The three cloud tools: get_weather, get_mandi_price, lookup_scheme. Data comes from frozen snapshots in data/snapshots/
so evaluation is repeatable (PLAN.md section 8). Live weather is only used with live=True.

Every tool returns a dict on success or an error STRING starting with 'ERROR <code>:' so the model can read it and retry.
Fetch the snapshots with: python -m src.cloud.fetch_snapshots  (see docs/cloud/README.md).
"""
import json
import re
from datetime import date
from pathlib import Path

SNAP = Path("data/snapshots")
CROPS = {"wheat": "Wheat", "paddy": "Paddy(Dhan)", "mustard": "Mustard", "sugarcane": "Sugarcane"}  # the 4 project crops
# KCC spellings and common alternates -> the name used in places.json
ALIASES = {"prayagraj": "allahabad", "ayodhya": "faizabad", "lakhimpur kheri": "kheri", "lakhimpur": "kheri",
           "bulandshahr": "bulandshahar", "budaun": "badaun", "maharajganj": "maharahganj", "kushinagar": "kushi nagar",
           "raebareli": "raebareli", "rae bareli": "raebareli", "amethi": "amethi ( shahu ji maharaj)"}

SPECS = [
    {"name": "get_weather",
     "description": "Use when the farmer asks about weather, rain or temperature in a named Uttar Pradesh district. Do not use for prices, schemes or crop advice, and do not guess a district the farmer did not name.",
     "parameters": {"type": "object", "properties": {
         "district": {"type": "string", "description": "English district name as spelled by Kisan Call Centre, e.g. 'Bareilly' or 'Kheri'. Not Hindi script."},
         "days": {"type": "integer", "description": "Forecast days, 1 to 7 (default 3)."}}, "required": ["district"]}},
    {"name": "get_mandi_price",
     "description": "Use when the farmer asks the market price of wheat, paddy, mustard or sugarcane at a named mandi or district. Do not use for weather, schemes or price predictions.",
     "parameters": {"type": "object", "properties": {
         "crop": {"type": "string", "enum": list(CROPS), "description": "Lowercase English crop name, not Hindi."},
         "mandi": {"type": "string", "description": "Mandi or district name in English, e.g. 'Bareilly'."}}, "required": ["crop", "mandi"]}},
    {"name": "lookup_scheme",
     "description": "Use when the farmer asks about PM-KISAN, PMFBY crop insurance, Kisan Credit Card, Soil Health Card or the Kisan Call Centre. Do not use for any other topic.",
     "parameters": {"type": "object", "properties": {
         "scheme": {"type": "string", "description": "Scheme name in English, e.g. 'pm-kisan', 'pmfby', 'kcc loan', 'soil health card'."}},
         "required": ["scheme"]}},
]


def err(code, msg):
    return f"ERROR {code}: {msg}"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else None


def _latest(pattern, as_of):
    """Newest snapshot file whose date (last _YYYY-MM-DD in its name) is <= as_of."""
    ok = [p for p in SNAP.glob(pattern) if (m := re.search(r"(\d{4}-\d{2}-\d{2})", p.stem)) and m.group(1) <= as_of]
    return max(ok, key=lambda p: re.search(r"(\d{4}-\d{2}-\d{2})", p.stem).group(1), default=None)


class Tools:
    def __init__(self, as_of=None, live=False):
        self.as_of, self.live = as_of or date.today().isoformat(), live
        self.places = _load(SNAP / "places.json") or {}

    def specs(self):
        return SPECS

    def call(self, name, args):
        """Returns (result, status). status is 'ok' or 'error'. Result is a dict or an ERROR string."""
        fn = getattr(self, f"_{name}", None)
        if fn is None:
            return err("unknown_tool", f"no tool named '{name}'; use one of {[s['name'] for s in SPECS]}"), "error"
        try:
            res = fn(**(args or {}))
        except TypeError as e:
            res = err("invalid_argument", f"{e}")
        return res, ("error" if isinstance(res, str) else "ok")

    def _place(self, district):
        key = re.sub(r"\s+", " ", str(district).strip().lower())
        key = ALIASES.get(key, key)
        for k, v in self.places.items():
            if k.lower() == key:
                return k, v
        return None, None

    def _get_weather(self, district, days=3):
        if not isinstance(days, int) or not 1 <= days <= 7:
            return err("invalid_argument", f"days '{days}' must be an integer from 1 to 7.")
        name, p = self._place(district)
        if not p:
            return err("invalid_argument", f"district '{district}' is not a known UP district; use the English spelling, e.g. 'Bareilly'.")
        snap = _latest(f"weather/{name.replace(' ', '_')}_*.json", self.as_of)
        if snap is None:
            return err("no_data", f"no weather snapshot for '{name}' on or before {self.as_of}.")
        d = json.loads(snap.read_text(encoding="utf-8"))["daily"]
        rows = [{"date": d["time"][i], "max_c": d["temperature_2m_max"][i], "min_c": d["temperature_2m_min"][i],
                 "rain_mm": d["precipitation_sum"][i], "rain_chance_pct": d["precipitation_probability_max"][i]}
                for i in range(min(days, len(d["time"])))]
        return {"district": name, "as_of": re.search(r"\d{4}-\d{2}-\d{2}", snap.stem).group(0), "forecast": rows}

    def _get_mandi_price(self, crop, mandi):
        if crop not in CROPS:
            return err("invalid_argument", f"crop '{crop}' must be one of {list(CROPS)} (lowercase English).")
        if not str(mandi).strip():
            return err("invalid_argument", "mandi must be a non-empty English name.")
        snap = _latest("mandi_*.json", self.as_of)
        if snap is None:
            return err("no_data", f"no mandi price snapshot on or before {self.as_of}.")
        m = str(mandi).strip().lower()
        rows = [r for r in json.loads(snap.read_text(encoding="utf-8"))
                if r["commodity"].lower().startswith(CROPS[crop].lower().split("(")[0]) and (m in r["market"].lower() or m in r["district"].lower())]
        if not rows:
            return err("no_data", f"no {crop} price at '{mandi}' in snapshot {snap.stem[-10:]}.")
        r = max(rows, key=lambda r: r["arrival_date"])
        return {"crop": crop, "market": r["market"], "district": r["district"], "price_date": r["arrival_date"],
                "min": r["min_price"], "max": r["max_price"], "modal": r["modal_price"], "unit": "Rs per quintal",
                "as_of": snap.stem[-10:]}

    def _lookup_scheme(self, scheme):
        data = _load(SNAP / "schemes.json") or {}
        s = re.sub(r"[^a-z0-9 ]", " ", str(scheme).lower())
        for key, v in data.items():
            if any(a in s for a in v["aliases"]):
                return {k: v[k] for k in v if k != "aliases"} | {"scheme": key}
        return err("no_data", f"no scheme matching '{scheme}'; known: {list(data)}.")
