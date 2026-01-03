# constants.py

TAG_KEYS = ["amenity", "shop", "leisure", "highway", "railway", "public_transport"]
STANDARD_COLS = ["id", "geometry", "category"]

SERVICE_DEFINITIONS = {
    "healthcare": {
        "amenity": ["hospital", "clinic", "doctors", "pharmacy"]
    },
    "education_early": {
        "amenity": ["kindergarten"]
    },
    "education_school": {
        "amenity": ["school"]
    },
    "education_higher": {
        "amenity": ["college", "university"]
    },
    "food": {
        "shop": ["supermarket", "convenience", "greengrocer", "bakery"]
    },
    "emergency": {
        "amenity": ["fire_station", "police", "ambulance_station"]
    },
    "green_space": {
        "leisure": ["park"]
    },
    "public_transport": {
        "highway": ["bus_stop"],
        "railway": ["station"],
        "public_transport": ["station"]
    }
}
