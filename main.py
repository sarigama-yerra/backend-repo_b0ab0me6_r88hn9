import os
from datetime import datetime, date
from typing import List, Optional, Dict, Any

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Shabbat Times API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class City(BaseModel):
    slug: str
    name: str
    country: str
    latitude: float
    longitude: float
    tzid: str


# Curated list of major cities worldwide
CITIES: List[City] = [
    City(slug="new-york", name="New York", country="USA", latitude=40.7128, longitude=-74.0060, tzid="America/New_York"),
    City(slug="los-angeles", name="Los Angeles", country="USA", latitude=34.0522, longitude=-118.2437, tzid="America/Los_Angeles"),
    City(slug="miami", name="Miami", country="USA", latitude=25.7617, longitude=-80.1918, tzid="America/New_York"),
    City(slug="london", name="London", country="UK", latitude=51.5072, longitude=-0.1276, tzid="Europe/London"),
    City(slug="paris", name="Paris", country="France", latitude=48.8566, longitude=2.3522, tzid="Europe/Paris"),
    City(slug="jerusalem", name="Jerusalem", country="Israel", latitude=31.7683, longitude=35.2137, tzid="Asia/Jerusalem"),
    City(slug="tel-aviv", name="Tel Aviv", country="Israel", latitude=32.0853, longitude=34.7818, tzid="Asia/Jerusalem"),
    City(slug="toronto", name="Toronto", country="Canada", latitude=43.6532, longitude=-79.3832, tzid="America/Toronto"),
    City(slug="montreal", name="Montreal", country="Canada", latitude=45.5019, longitude=-73.5674, tzid="America/Toronto"),
    City(slug="sydney", name="Sydney", country="Australia", latitude=-33.8688, longitude=151.2093, tzid="Australia/Sydney"),
    City(slug="melbourne", name="Melbourne", country="Australia", latitude=-37.8136, longitude=144.9631, tzid="Australia/Melbourne"),
    City(slug="johannesburg", name="Johannesburg", country="South Africa", latitude=-26.2041, longitude=28.0473, tzid="Africa/Johannesburg"),
    City(slug="mexico-city", name="Mexico City", country="Mexico", latitude=19.4326, longitude=-99.1332, tzid="America/Mexico_City"),
    City(slug="buenos-aires", name="Buenos Aires", country="Argentina", latitude=-34.6037, longitude=-58.3816, tzid="America/Argentina/Buenos_Aires"),
    City(slug="sao-paulo", name="São Paulo", country="Brazil", latitude=-23.5505, longitude=-46.6333, tzid="America/Sao_Paulo"),
    City(slug="madrid", name="Madrid", country="Spain", latitude=40.4168, longitude=-3.7038, tzid="Europe/Madrid"),
    City(slug="rome", name="Rome", country="Italy", latitude=41.9028, longitude=12.4964, tzid="Europe/Rome"),
    City(slug="moscow", name="Moscow", country="Russia", latitude=55.7558, longitude=37.6173, tzid="Europe/Moscow"),
    City(slug="singapore", name="Singapore", country="Singapore", latitude=1.3521, longitude=103.8198, tzid="Asia/Singapore"),
    City(slug="hong-kong", name="Hong Kong", country="China", latitude=22.3193, longitude=114.1694, tzid="Asia/Hong_Kong"),
]


class ShabbatTimes(BaseModel):
    city: City
    date: date
    parsha: Optional[str] = None
    candle_lighting: Optional[str] = None
    havdalah: Optional[str] = None
    source: str
    raw: Dict[str, Any]


def fetch_shabbat_times_from_hebcal(city: City) -> ShabbatTimes:
    # Hebcal JSON API for Shabbat times
    url = (
        "https://www.hebcal.com/shabbat?cfg=json"
        f"&latitude={city.latitude}&longitude={city.longitude}"
        f"&tzid={city.tzid}&m=50"
    )
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="Upstream provider error")
    data = r.json()

    candle = None
    havdalah = None
    parsha = None

    for item in data.get("items", []):
        cat = item.get("category")
        if cat == "candles" and candle is None:
            candle = item.get("title")  # e.g., "Candle lighting: 7:01pm"
            # Extract time after colon
            if candle and ":" in candle:
                candle = candle.split(":", 1)[1].strip()
        if cat == "havdalah" and havdalah is None:
            hv = item.get("title")
            if hv and ":" in hv:
                havdalah = hv.split(":", 1)[1].strip()
        if cat == "parashat" and parsha is None:
            parsha = item.get("hebrew") or item.get("title")

    times = ShabbatTimes(
        city=city,
        date=date.today(),
        parsha=parsha,
        candle_lighting=candle,
        havdalah=havdalah,
        source="hebcal.com",
        raw=data,
    )
    return times


@app.get("/")
def read_root():
    return {"message": "Shabbat Times API is running"}


@app.get("/api/cities", response_model=List[City])
def list_cities() -> List[City]:
    return CITIES


@app.get("/api/shabbat", response_model=ShabbatTimes)
def get_shabbat_times(city: str = Query(..., description="City slug from /api/cities")) -> ShabbatTimes:
    city_obj = next((c for c in CITIES if c.slug == city), None)
    if not city_obj:
        raise HTTPException(status_code=404, detail="City not found")

    # For now, use Hebcal as the reliable provider. We can switch to chabad.org if a stable endpoint is provided.
    return fetch_shabbat_times_from_hebcal(city_obj)


@app.get("/test")
def test_database():
    """Simple health check (no DB required for this app)."""
    return {
        "backend": "✅ Running",
        "cities_count": len(CITIES),
        "example_city": CITIES[0].model_dump(),
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
